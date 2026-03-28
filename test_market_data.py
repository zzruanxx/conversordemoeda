import time

from market_data import (
    CryptoProvider,
    FiatProvider,
    MarketDataService,
    normalize_symbol,
)


class FailingCryptoProvider(CryptoProvider):
    name = "crypto-primary-fail"

    def fetch_rates_to_usd(self, symbols):
        raise RuntimeError("provider down")


class FallbackCryptoProvider(CryptoProvider):
    name = "crypto-fallback-ok"

    def __init__(self):
        self.calls = 0

    def fetch_rates_to_usd(self, symbols):
        self.calls += 1
        return {"BTC": 65000.0, "ETH": 3200.0, "USDT": 1.0}


class FailingFiatProvider(FiatProvider):
    name = "fiat-primary-fail"

    def fetch_rates_to_usd(self, symbols):
        raise RuntimeError("provider down")


class FallbackFiatProvider(FiatProvider):
    name = "fiat-fallback-ok"

    def __init__(self):
        self.calls = 0

    def fetch_rates_to_usd(self, symbols):
        self.calls += 1
        return {"USD": 1.0, "BRL": 0.20, "EUR": 1.10, "COP": 0.00025, "PEN": 0.28}


def test_symbol_normalization_aliases():
    assert normalize_symbol("btc") == "BTC"
    assert normalize_symbol("xbt") == "BTC"
    assert normalize_symbol("us$") == "USD"
    assert normalize_symbol("r$") == "BRL"


def test_market_service_fallback_and_sources():
    crypto_fallback = FallbackCryptoProvider()
    fiat_fallback = FallbackFiatProvider()
    service = MarketDataService(
        crypto_providers=[FailingCryptoProvider(), crypto_fallback],
        fiat_providers=[FailingFiatProvider(), fiat_fallback],
        ttl_seconds=20,
    )

    snapshot = service.get_snapshot(allow_network=True)

    assert snapshot["sources"]["crypto"] == "crypto-fallback-ok"
    assert snapshot["sources"]["fiat"] == "fiat-fallback-ok"
    assert "BTC" in snapshot["symbols"]
    assert "USD" in snapshot["symbols"]
    assert snapshot["rates_to_usd"]["BTC"] == 65000.0
    assert snapshot["rates_to_usd"]["BRL"] == 0.20
    assert crypto_fallback.calls == 1
    assert fiat_fallback.calls == 1


def test_market_service_cache_uses_ttl():
    crypto_fallback = FallbackCryptoProvider()
    fiat_fallback = FallbackFiatProvider()
    service = MarketDataService(
        crypto_providers=[crypto_fallback],
        fiat_providers=[fiat_fallback],
        ttl_seconds=30,
    )

    first = service.get_snapshot(allow_network=True)
    second = service.get_snapshot(allow_network=True)

    assert first["updated_at"] == second["updated_at"]
    assert crypto_fallback.calls == 1
    assert fiat_fallback.calls == 1


def test_market_service_refresh_after_ttl_expiration():
    crypto_fallback = FallbackCryptoProvider()
    fiat_fallback = FallbackFiatProvider()
    service = MarketDataService(
        crypto_providers=[crypto_fallback],
        fiat_providers=[fiat_fallback],
        ttl_seconds=1,
    )

    first = service.get_snapshot(allow_network=True)
    time.sleep(1.1)
    second = service.get_snapshot(allow_network=True)

    assert first["updated_at"] != second["updated_at"]
    assert crypto_fallback.calls == 2
    assert fiat_fallback.calls == 2


def test_market_service_without_network_returns_static_or_cache():
    service = MarketDataService(
        crypto_providers=[FailingCryptoProvider()],
        fiat_providers=[FailingFiatProvider()],
        ttl_seconds=20,
    )

    snapshot = service.get_snapshot(allow_network=False)

    assert snapshot["sources"]["crypto"] == "static-fallback"
    assert snapshot["sources"]["fiat"] == "static-fallback"
    assert "updated_at" in snapshot
    assert snapshot["rates_to_usd"]["USD"] == 1.0
