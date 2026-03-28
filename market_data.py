"""Market data providers with caching, fallback, and symbol normalization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import threading
import time
from typing import Dict, Iterable, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_RATES_TO_USD: Dict[str, float] = {
    "USD": 1.0,
    "USDT": 1.0,
    "BRL": 0.18,
    "EUR": 1.08,
    "COP": 0.00024,
    "PEN": 0.27,
    "BTC": 60000.0,
    "ETH": 3000.0,
}

# Canonical symbols expected by the application.
STANDARD_SYMBOLS = ("BTC", "ETH", "USDT", "BRL", "USD", "EUR")

SYMBOL_ALIASES = {
    "XBT": "BTC",
    "US$": "USD",
    "R$": "BRL",
}


def normalize_symbol(symbol: str) -> str:
    """Normalize user/provider symbol variations to canonical uppercase symbols."""
    cleaned = str(symbol).strip().upper()
    return SYMBOL_ALIASES.get(cleaned, cleaned)


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _http_get_json(url: str, timeout: float = 2.0) -> Mapping[str, object]:
    req = Request(url, headers={"User-Agent": "conversordemoeda/1.0"})
    try:
        with urlopen(req, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise RuntimeError(f"Failed to fetch market data from {url}: {exc}") from exc


class CryptoProvider:
    name = "base-crypto"

    def fetch_rates_to_usd(self, symbols: Iterable[str]) -> Dict[str, float]:
        raise NotImplementedError


class FiatProvider:
    name = "base-fiat"

    def fetch_rates_to_usd(self, symbols: Iterable[str]) -> Dict[str, float]:
        raise NotImplementedError


class CoinGeckoCryptoProvider(CryptoProvider):
    name = "coingecko"

    def fetch_rates_to_usd(self, symbols: Iterable[str]) -> Dict[str, float]:
        needed = {normalize_symbol(sym) for sym in symbols}
        ids = {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "USDT": "tether",
        }
        request_ids = [ids[sym] for sym in ids if sym in needed]
        if not request_ids:
            return {}

        url = (
            "https://api.coingecko.com/api/v3/simple/price?"
            f"ids={','.join(request_ids)}&vs_currencies=usd"
        )
        data = _http_get_json(url)
        out: Dict[str, float] = {}
        reverse_ids = {v: k for k, v in ids.items()}

        for asset_id, values in data.items():
            if not isinstance(values, Mapping):
                continue
            usd = values.get("usd")
            if isinstance(usd, (int, float)) and usd > 0:
                out[reverse_ids[asset_id]] = float(usd)
        return out


class BinanceCryptoProvider(CryptoProvider):
    name = "binance"

    def fetch_rates_to_usd(self, symbols: Iterable[str]) -> Dict[str, float]:
        needed = {normalize_symbol(sym) for sym in symbols}
        symbol_map = {
            "BTC": "BTCUSDT",
            "ETH": "ETHUSDT",
        }
        out: Dict[str, float] = {}

        for symbol, pair in symbol_map.items():
            if symbol not in needed:
                continue
            data = _http_get_json(f"https://api.binance.com/api/v3/ticker/price?symbol={pair}")
            price = data.get("price")
            try:
                numeric = float(price)
            except (TypeError, ValueError):
                continue
            if numeric > 0:
                out[symbol] = numeric

        if "USDT" in needed:
            out["USDT"] = 1.0
        return out


class ExchangeRateHostFiatProvider(FiatProvider):
    name = "exchangerate-host"

    def fetch_rates_to_usd(self, symbols: Iterable[str]) -> Dict[str, float]:
        needed = {normalize_symbol(sym) for sym in symbols}
        needed.add("USD")
        wanted = ",".join(sorted(needed))
        url = f"https://api.exchangerate.host/live?source=USD&currencies={wanted}"
        data = _http_get_json(url)

        quotes = data.get("quotes")
        if not isinstance(quotes, Mapping):
            raise RuntimeError("Invalid exchangerate.host response format")

        out: Dict[str, float] = {"USD": 1.0}
        for symbol in needed:
            if symbol == "USD":
                continue
            quote_key = f"USD{symbol}"
            raw = quotes.get(quote_key)
            if not isinstance(raw, (int, float)):
                continue
            if raw <= 0:
                continue
            out[symbol] = 1.0 / float(raw)
        return out


class FrankfurterFiatProvider(FiatProvider):
    name = "frankfurter"

    def fetch_rates_to_usd(self, symbols: Iterable[str]) -> Dict[str, float]:
        needed = {normalize_symbol(sym) for sym in symbols}
        needed.add("USD")
        to_symbols = ",".join(sorted(sym for sym in needed if sym != "USD"))
        url = f"https://api.frankfurter.app/latest?from=USD&to={to_symbols}"
        data = _http_get_json(url)
        rates = data.get("rates")
        if not isinstance(rates, Mapping):
            raise RuntimeError("Invalid frankfurter response format")

        out: Dict[str, float] = {"USD": 1.0}
        for symbol in needed:
            if symbol == "USD":
                continue
            raw = rates.get(symbol)
            if not isinstance(raw, (int, float)):
                continue
            if raw <= 0:
                continue
            out[symbol] = 1.0 / float(raw)
        return out


@dataclass
class ProviderResult:
    rates: Dict[str, float]
    source: str


class MarketDataService:
    """Fetches market data with provider fallback and short-lived cache."""

    def __init__(
        self,
        crypto_providers: Iterable[CryptoProvider] | None = None,
        fiat_providers: Iterable[FiatProvider] | None = None,
        ttl_seconds: int = 20,
    ) -> None:
        self.crypto_providers = list(
            crypto_providers
            if crypto_providers is not None
            else [CoinGeckoCryptoProvider(), BinanceCryptoProvider()]
        )
        self.fiat_providers = list(
            fiat_providers
            if fiat_providers is not None
            else [ExchangeRateHostFiatProvider(), FrankfurterFiatProvider()]
        )
        self.ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._cache_snapshot: Dict[str, object] | None = None
        self._cache_monotonic = 0.0

    def get_snapshot(
        self,
        force_refresh: bool = False,
        allow_network: bool = True,
    ) -> Dict[str, object]:
        with self._lock:
            now = time.monotonic()
            has_fresh_cache = (
                self._cache_snapshot is not None
                and (now - self._cache_monotonic) <= self.ttl_seconds
            )

            if not force_refresh and has_fresh_cache:
                return dict(self._cache_snapshot)

            if not allow_network:
                if self._cache_snapshot is not None:
                    return dict(self._cache_snapshot)
                snapshot = self._build_static_snapshot()
                self._cache_snapshot = snapshot
                self._cache_monotonic = now
                return dict(snapshot)

            snapshot = self._build_live_snapshot()
            self._cache_snapshot = snapshot
            self._cache_monotonic = now
            return dict(snapshot)

    def _build_live_snapshot(self) -> Dict[str, object]:
        crypto_symbols = ["BTC", "ETH", "USDT"]
        fiat_symbols = ["USD", "BRL", "EUR", "COP", "PEN"]

        crypto_result = self._fetch_with_fallback(self.crypto_providers, crypto_symbols)
        fiat_result = self._fetch_with_fallback(self.fiat_providers, fiat_symbols)

        rates: Dict[str, float] = dict(DEFAULT_RATES_TO_USD)
        rates.update(fiat_result.rates)
        rates.update(crypto_result.rates)

        timestamp = _now_iso()
        return {
            "rates_to_usd": rates,
            "symbols": list(STANDARD_SYMBOLS),
            "updated_at": timestamp,
            "updated_at_unix": int(datetime.now(timezone.utc).timestamp()),
            "sources": {
                "crypto": crypto_result.source,
                "fiat": fiat_result.source,
            },
        }

    def _build_static_snapshot(self) -> Dict[str, object]:
        timestamp = _now_iso()
        return {
            "rates_to_usd": dict(DEFAULT_RATES_TO_USD),
            "symbols": list(STANDARD_SYMBOLS),
            "updated_at": timestamp,
            "updated_at_unix": int(datetime.now(timezone.utc).timestamp()),
            "sources": {
                "crypto": "static-fallback",
                "fiat": "static-fallback",
            },
        }

    @staticmethod
    def _fetch_with_fallback(
        providers: Iterable[CryptoProvider | FiatProvider],
        symbols: Iterable[str],
    ) -> ProviderResult:
        target_symbols = {normalize_symbol(sym) for sym in symbols}
        for provider in providers:
            try:
                data = provider.fetch_rates_to_usd(target_symbols)
            except Exception:
                continue

            clean: Dict[str, float] = {}
            for key, raw in data.items():
                symbol = normalize_symbol(key)
                if symbol not in target_symbols:
                    continue
                try:
                    value = float(raw)
                except (TypeError, ValueError):
                    continue
                if value > 0:
                    clean[symbol] = value

            if clean:
                return ProviderResult(rates=clean, source=provider.name)

        fallback = {
            sym: DEFAULT_RATES_TO_USD[sym]
            for sym in target_symbols
            if sym in DEFAULT_RATES_TO_USD
        }
        return ProviderResult(rates=fallback, source="static-fallback")