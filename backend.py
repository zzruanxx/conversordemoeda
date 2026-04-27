"""Core backend logic for currency/crypto conversion."""

from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping

from market_data import (
    DEFAULT_RATES_TO_USD,
    MarketDataService,
    STANDARD_SYMBOLS,
    normalize_symbol,
)

# Exchange rate constants (1 unit = USD)
COP_TO_USD = 0.00024  # Colombian Peso to USD
PEN_TO_USD = 0.27  # Peruvian Sol to USD
BRL_TO_USD = 0.18  # Brazilian Real to USD
BTC_TO_USD = 60000.00  # Bitcoin to USD
ETH_TO_USD = 3000.00  # Ethereum to USD
USDT_TO_USD = 1.00  # Tether to USD
EUR_TO_USD = 1.08  # Euro to USD

# Exchange rate display helpers (1 USD = currency)
USD_TO_COP = 4166.67
USD_TO_PEN = 3.70
USD_TO_BRL = 5.55

_MARKET_DATA = MarketDataService(ttl_seconds=20)

DECIMAL_ZERO = Decimal("0")
DECIMAL_ONE = Decimal("1")
DECIMAL_HUNDRED = Decimal("100")
CRYPTO_SYMBOLS = {"BTC", "ETH", "USDT", "BNB", "SOL", "XRP", "ADA", "DOGE"}

# Ordered lists used for the crypto monitoring feature
MONITOR_CRYPTOS = ["BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE"]
MONITOR_FIATS = ["USD", "EUR", "BRL", "GBP", "JPY"]


def _to_decimal(raw: Any) -> Decimal:
    if isinstance(raw, Decimal):
        return raw
    return Decimal(str(raw))


def _decimal_to_float(value: Decimal) -> float:
    return float(value)


def _decimal_to_str(value: Decimal) -> str:
    normalized = value.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _parse_non_negative_decimal(raw: Any, name: str) -> Decimal:
    try:
        numeric = _to_decimal(raw)
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ValueError(f"Valor inválido '{raw}' para {name}") from exc
    if numeric < DECIMAL_ZERO:
        raise ValueError(f"Valor negativo {numeric} não permitido para {name}")
    return numeric


def _parse_percentage(raw: Any, name: str) -> Decimal:
    numeric = _parse_non_negative_decimal(raw, name)
    if numeric >= DECIMAL_HUNDRED:
        raise ValueError(f"{name} deve ser menor que 100")
    return numeric


def _resolve_rates_to_usd_decimals(rates_to_usd: Mapping[str, Any] | None = None) -> Dict[str, Decimal]:
    merged: Dict[str, Decimal] = {}

    for symbol, raw in DEFAULT_RATES_TO_USD.items():
        normalized = normalize_symbol(symbol)
        try:
            numeric = _to_decimal(raw)
        except (TypeError, ValueError, InvalidOperation):
            continue
        if numeric > DECIMAL_ZERO:
            merged[normalized] = numeric

    if rates_to_usd is not None:
        for symbol, raw in rates_to_usd.items():
            normalized = normalize_symbol(symbol)
            try:
                numeric = _to_decimal(raw)
            except (TypeError, ValueError, InvalidOperation):
                continue
            if numeric > DECIMAL_ZERO:
                merged[normalized] = numeric

    merged["USD"] = DECIMAL_ONE
    return merged


def _convert_via_usd(
    amount: Decimal,
    from_rate_to_usd: Decimal,
    to_rate_to_usd: Decimal,
    fee_percent: Decimal,
    spread_percent: Decimal,
) -> Dict[str, Decimal]:
    gross = (amount * from_rate_to_usd) / to_rate_to_usd
    spread_amount = gross * (spread_percent / DECIMAL_HUNDRED)
    after_spread = gross - spread_amount
    fee_amount = after_spread * (fee_percent / DECIMAL_HUNDRED)
    net = after_spread - fee_amount
    return {
        "gross": gross,
        "spread_amount": spread_amount,
        "after_spread": after_spread,
        "fee_amount": fee_amount,
        "net": net,
    }


def get_market_snapshot(
    force_refresh: bool = False,
    allow_network: bool = True,
) -> Dict[str, object]:
    """Get market snapshot with standardized symbols, timestamp and source metadata."""
    return _MARKET_DATA.get_snapshot(force_refresh=force_refresh, allow_network=allow_network)


def get_rates(allow_network: bool = True) -> Dict[str, Any]:
    snapshot = get_market_snapshot(allow_network=allow_network)
    rates_to_usd = snapshot.get("rates_to_usd", {})
    rates_decimals = _resolve_rates_to_usd_decimals(rates_to_usd)

    def _rate(symbol: str, fallback: float) -> float:
        raw = rates_decimals.get(normalize_symbol(symbol), _to_decimal(fallback))
        try:
            value = float(raw)
        except (TypeError, ValueError, InvalidOperation):
            return fallback
        return value if value > 0 else fallback

    cop_to_usd = _rate("COP", COP_TO_USD)
    pen_to_usd = _rate("PEN", PEN_TO_USD)
    brl_to_usd = _rate("BRL", BRL_TO_USD)
    btc_to_usd = _rate("BTC", BTC_TO_USD)
    eth_to_usd = _rate("ETH", ETH_TO_USD)
    usdt_to_usd = _rate("USDT", USDT_TO_USD)
    eur_to_usd = _rate("EUR", EUR_TO_USD)

    return {
        "COP_TO_USD": cop_to_usd,
        "PEN_TO_USD": pen_to_usd,
        "BRL_TO_USD": brl_to_usd,
        "BTC_TO_USD": btc_to_usd,
        "ETH_TO_USD": eth_to_usd,
        "USDT_TO_USD": usdt_to_usd,
        "EUR_TO_USD": eur_to_usd,
        "USD_TO_COP": 1.0 / cop_to_usd if cop_to_usd else USD_TO_COP,
        "USD_TO_PEN": 1.0 / pen_to_usd if pen_to_usd else USD_TO_PEN,
        "USD_TO_BRL": 1.0 / brl_to_usd if brl_to_usd else USD_TO_BRL,
        "SYMBOLS": list(snapshot.get("symbols", list(STANDARD_SYMBOLS))),
        "RATES_TO_USD": {
            symbol: _decimal_to_float(value)
            for symbol, value in rates_decimals.items()
        },
        "ASSET_CATALOG": get_asset_catalog(rates_to_usd=rates_to_usd),
        "UPDATED_AT": snapshot.get("updated_at"),
        "UPDATED_AT_UNIX": snapshot.get("updated_at_unix"),
        "SOURCES": snapshot.get("sources", {}),
    }


def get_asset_catalog(
    allow_network: bool = True,
    rates_to_usd: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    snapshot: Dict[str, object] | None = None
    source_rates = rates_to_usd

    if source_rates is None:
        snapshot = get_market_snapshot(allow_network=allow_network)
        source_rates = snapshot.get("rates_to_usd", {})

    rates_decimals = _resolve_rates_to_usd_decimals(source_rates)
    assets: Dict[str, Dict[str, Any]] = {}

    for symbol in sorted(rates_decimals.keys()):
        rate = rates_decimals[symbol]
        assets[symbol] = {
            "symbol": symbol,
            "category": "crypto" if symbol in CRYPTO_SYMBOLS else "fiat",
            "rate_to_usd": _decimal_to_float(rate),
            "rate_to_usd_decimal": _decimal_to_str(rate),
        }

    return {
        "assets": assets,
        "symbols": list(assets.keys()),
        "updated_at": snapshot.get("updated_at") if snapshot else None,
        "sources": snapshot.get("sources", {}) if snapshot else {},
    }


def convert_asset_amount(
    amount: Any,
    from_symbol: str,
    to_symbol: str = "USD",
    fee_percent: Any = 0,
    spread_percent: Any = 0,
    rates_to_usd: Mapping[str, Any] | None = None,
    allow_network: bool = True,
) -> Dict[str, Any]:
    from_normalized = normalize_symbol(from_symbol)
    to_normalized = normalize_symbol(to_symbol)

    amount_dec = _parse_non_negative_decimal(amount, f"Valor para {from_normalized}")
    fee_dec = _parse_percentage(fee_percent, "fee_percent")
    spread_dec = _parse_percentage(spread_percent, "spread_percent")

    source_rates = rates_to_usd
    if source_rates is None:
        snapshot = get_market_snapshot(allow_network=allow_network)
        source_rates = snapshot.get("rates_to_usd", {})

    rates_decimals = _resolve_rates_to_usd_decimals(source_rates)
    if from_normalized not in rates_decimals:
        raise ValueError(f"Ativo de origem não suportado: {from_normalized}")
    if to_normalized not in rates_decimals:
        raise ValueError(f"Ativo de destino não suportado: {to_normalized}")

    from_rate = rates_decimals[from_normalized]
    to_rate = rates_decimals[to_normalized]
    converted = _convert_via_usd(
        amount=amount_dec,
        from_rate_to_usd=from_rate,
        to_rate_to_usd=to_rate,
        fee_percent=fee_dec,
        spread_percent=spread_dec,
    )

    return {
        "amount": _decimal_to_float(amount_dec),
        "amount_decimal": _decimal_to_str(amount_dec),
        "from_symbol": from_normalized,
        "to_symbol": to_normalized,
        "fee_percent": _decimal_to_float(fee_dec),
        "spread_percent": _decimal_to_float(spread_dec),
        "rates_to_usd": {
            "from": _decimal_to_float(from_rate),
            "to": _decimal_to_float(to_rate),
        },
        "result": {
            "gross": _decimal_to_float(converted["gross"]),
            "spread_amount": _decimal_to_float(converted["spread_amount"]),
            "after_spread": _decimal_to_float(converted["after_spread"]),
            "fee_amount": _decimal_to_float(converted["fee_amount"]),
            "net": _decimal_to_float(converted["net"]),
            "net_decimal": _decimal_to_str(converted["net"]),
        },
    }


def convert_amounts(
    pesos: Any = 0.0,
    soles: Any = 0.0,
    reais: Any = 0.0,
    btc: Any = 0.0,
    eth: Any = 0.0,
    rates_to_usd: Mapping[str, Any] | None = None,
    fee_percent: Any = 0,
    spread_percent: Any = 0,
) -> Dict[str, Dict[str, float] | float | Dict[str, float] | Dict[str, Dict[str, float]]]:
    fields = {
        "pesos": ("Pesos Colombianos (COP)", pesos),
        "soles": ("Soles Peruanos (PEN)", soles),
        "reais": ("Reais Brasileiros (BRL)", reais),
        "btc": ("Bitcoin (BTC)", btc),
        "eth": ("Ethereum (ETH)", eth),
    }
    field_symbols = {
        "pesos": "COP",
        "soles": "PEN",
        "reais": "BRL",
        "btc": "BTC",
        "eth": "ETH",
    }

    values: Dict[str, Decimal] = {}
    for key, (name, raw) in fields.items():
        numeric = _parse_non_negative_decimal(raw, name)
        values[key] = numeric

    fee_dec = _parse_percentage(fee_percent, "fee_percent")
    spread_dec = _parse_percentage(spread_percent, "spread_percent")
    rates_decimals = _resolve_rates_to_usd_decimals(rates_to_usd)
    usd_rate = rates_decimals["USD"]

    usd_values: Dict[str, Decimal] = {}
    pricing_breakdown: Dict[str, Dict[str, float]] = {}

    for field, amount in values.items():
        symbol = field_symbols[field]
        rate = rates_decimals.get(symbol)
        if rate is None:
            raise ValueError(f"Ativo não suportado para conversão: {symbol}")

        converted = _convert_via_usd(
            amount=amount,
            from_rate_to_usd=rate,
            to_rate_to_usd=usd_rate,
            fee_percent=fee_dec,
            spread_percent=spread_dec,
        )
        usd_values[field] = converted["net"]
        pricing_breakdown[field] = {
            "gross": _decimal_to_float(converted["gross"]),
            "spread_amount": _decimal_to_float(converted["spread_amount"]),
            "fee_amount": _decimal_to_float(converted["fee_amount"]),
            "net": _decimal_to_float(converted["net"]),
        }

    total = sum(usd_values.values(), start=DECIMAL_ZERO)

    return {
        "inputs": {key: _decimal_to_float(value) for key, value in values.items()},
        "usd": {key: _decimal_to_float(value) for key, value in usd_values.items()},
        "total": _decimal_to_float(total),
        "pricing": {
            "fee_percent": _decimal_to_float(fee_dec),
            "spread_percent": _decimal_to_float(spread_dec),
            "breakdown": pricing_breakdown,
        },
    }


def get_crypto_prices_in_currencies(
    allow_network: bool = True,
    rates_to_usd: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Return the price of each major cryptocurrency expressed in major fiat currencies.

    The result contains a ``prices`` mapping of the form
    ``{crypto_symbol: {fiat_symbol: price_as_float}}``, plus metadata about
    which cryptos and currencies are available and when the data was last
    fetched.
    """
    snapshot_meta: Dict[str, object] | None = None
    source_rates = rates_to_usd

    if source_rates is None:
        snapshot_meta = get_market_snapshot(allow_network=allow_network)
        source_rates = snapshot_meta.get("rates_to_usd", {})

    rates_decimals = _resolve_rates_to_usd_decimals(source_rates)

    prices: Dict[str, Dict[str, float]] = {}
    for crypto in MONITOR_CRYPTOS:
        if crypto not in rates_decimals:
            continue
        crypto_rate_usd = rates_decimals[crypto]
        prices[crypto] = {}
        for fiat in MONITOR_FIATS:
            if fiat not in rates_decimals:
                continue
            fiat_rate_usd = rates_decimals[fiat]
            price = crypto_rate_usd / fiat_rate_usd
            prices[crypto][fiat] = _decimal_to_float(price)

    available_cryptos = [c for c in MONITOR_CRYPTOS if c in prices]
    available_fiats = [
        f for f in MONITOR_FIATS if any(f in p for p in prices.values())
    ]

    return {
        "cryptos": available_cryptos,
        "currencies": available_fiats,
        "prices": prices,
        "updated_at": snapshot_meta.get("updated_at") if snapshot_meta else None,
        "sources": snapshot_meta.get("sources", {}) if snapshot_meta else {},
    }
