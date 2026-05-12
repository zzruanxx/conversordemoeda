import time

from market_data import (
    CryptoProvider,
    FiatProvider,
    MarketDataService,
    normalize_symbol,
)

REQUIRED_SNAPSHOT_KEYS = ("rates_to_usd", "updated_at", "updated_at_unix", "sources", "symbols")


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


def test_symbol_normalization_leading_trailing_spaces():
    assert normalize_symbol("  btc  ") == "BTC"
    assert normalize_symbol("  USD  ") == "USD"


def test_symbol_normalization_already_uppercase():
    assert normalize_symbol("BTC") == "BTC"
    assert normalize_symbol("ETH") == "ETH"


def test_symbol_normalization_mixed_case():
    assert normalize_symbol("Eth") == "ETH"
    assert normalize_symbol("bRl") == "BRL"


def test_market_service_all_providers_fail_returns_static_fallback():
    """When every provider fails and there is no cache, the service returns
    static-fallback data with the expected keys."""
    service = MarketDataService(
        crypto_providers=[FailingCryptoProvider()],
        fiat_providers=[FailingFiatProvider()],
        ttl_seconds=20,
    )
    snapshot = service.get_snapshot(allow_network=False)

    assert "rates_to_usd" in snapshot
    assert "updated_at" in snapshot
    assert "sources" in snapshot
    assert "symbols" in snapshot
    for key in REQUIRED_SNAPSHOT_KEYS:
        assert key in snapshot, f"Missing key in static-fallback snapshot: {key}"
    assert snapshot["rates_to_usd"]["USD"] == 1.0
    assert snapshot["rates_to_usd"]["BTC"] > 0


def test_market_service_snapshot_has_all_required_keys():
    """A fresh snapshot from a working service must expose all expected keys."""
    service = MarketDataService(
        crypto_providers=[FallbackCryptoProvider()],
        fiat_providers=[FallbackFiatProvider()],
        ttl_seconds=30,
    )
    snapshot = service.get_snapshot(allow_network=True)

    for key in REQUIRED_SNAPSHOT_KEYS:
        assert key in snapshot, f"Missing key in snapshot: {key}"


def test_market_service_rates_to_usd_usd_always_one():
    """USD must always equal 1.0 in the rates mapping."""
    service = MarketDataService(
        crypto_providers=[FallbackCryptoProvider()],
        fiat_providers=[FallbackFiatProvider()],
        ttl_seconds=30,
    )
    snapshot = service.get_snapshot(allow_network=True)
    assert snapshot["rates_to_usd"].get("USD") == 1.0


def test_market_service_sources_contain_crypto_and_fiat():
    """The sources dict must always carry 'crypto' and 'fiat' entries."""
    service = MarketDataService(
        crypto_providers=[FallbackCryptoProvider()],
        fiat_providers=[FallbackFiatProvider()],
        ttl_seconds=30,
    )
    snapshot = service.get_snapshot(allow_network=True)
    assert "crypto" in snapshot["sources"]
    assert "fiat" in snapshot["sources"]


def test_market_service_cache_hit_does_not_re_call_providers():
    """Two consecutive calls within TTL must invoke each provider exactly once."""
    crypto = FallbackCryptoProvider()
    fiat = FallbackFiatProvider()
    service = MarketDataService(
        crypto_providers=[crypto],
        fiat_providers=[fiat],
        ttl_seconds=60,
    )
    service.get_snapshot(allow_network=True)
    service.get_snapshot(allow_network=True)
    service.get_snapshot(allow_network=True)

    assert crypto.calls == 1
    assert fiat.calls == 1


def test_market_service_force_refresh_bypasses_fresh_cache():
    class ChangingCryptoProvider(CryptoProvider):
        name = "crypto-changing"

        def __init__(self):
            self.calls = 0

        def fetch_rates_to_usd(self, symbols):
            price = 65000.0 + self.calls
            self.calls += 1
            return {"BTC": price, "ETH": 3200.0, "USDT": 1.0}

    class ChangingFiatProvider(FiatProvider):
        name = "fiat-changing"

        def __init__(self):
            self.calls = 0

        def fetch_rates_to_usd(self, symbols):
            brl_rate = 0.2 + (self.calls * 0.01)
            self.calls += 1
            return {"USD": 1.0, "BRL": brl_rate, "EUR": 1.10, "COP": 0.00025, "PEN": 0.28}

    crypto = ChangingCryptoProvider()
    fiat = ChangingFiatProvider()
    service = MarketDataService(
        crypto_providers=[crypto],
        fiat_providers=[fiat],
        ttl_seconds=60,
    )

    first = service.get_snapshot(allow_network=True)
    refreshed = service.get_snapshot(allow_network=True, force_refresh=True)

    assert crypto.calls == 2
    assert fiat.calls == 2
    assert refreshed["rates_to_usd"]["BTC"] != first["rates_to_usd"]["BTC"]
    assert refreshed["rates_to_usd"]["BRL"] != first["rates_to_usd"]["BRL"]


def test_market_service_allow_network_false_uses_cached_live_snapshot():
    crypto = FallbackCryptoProvider()
    fiat = FallbackFiatProvider()
    service = MarketDataService(
        crypto_providers=[crypto],
        fiat_providers=[fiat],
        ttl_seconds=60,
    )

    live_snapshot = service.get_snapshot(allow_network=True)
    assert crypto.calls == 1
    assert fiat.calls == 1

    cached_snapshot = service.get_snapshot(allow_network=False)

    assert cached_snapshot["sources"] == live_snapshot["sources"]
    assert cached_snapshot["rates_to_usd"] == live_snapshot["rates_to_usd"]
    assert cached_snapshot["updated_at"] == live_snapshot["updated_at"]
    assert cached_snapshot["updated_at_unix"] == live_snapshot["updated_at_unix"]
    assert cached_snapshot["symbols"] == live_snapshot["symbols"]
    assert crypto.calls == 1
    assert fiat.calls == 1


def test_market_service_allow_network_true_all_fail_returns_static_fallback():
    service = MarketDataService(
        crypto_providers=[FailingCryptoProvider()],
        fiat_providers=[FailingFiatProvider()],
        ttl_seconds=20,
    )

    snapshot = service.get_snapshot(allow_network=True)

    assert snapshot["sources"]["crypto"] == "static-fallback"
    assert snapshot["sources"]["fiat"] == "static-fallback"
    assert snapshot["rates_to_usd"]["USD"] == 1.0
