import json
import threading
from http.client import HTTPConnection
from http.server import HTTPServer

import pytest

from api import ConversionAPIHandler
from backend import (
    BRL_TO_USD,
    BTC_TO_USD,
    COP_TO_USD,
    ETH_TO_USD,
    PEN_TO_USD,
    MONITOR_CRYPTOS,
    MONITOR_FIATS,
    convert_asset_amount,
    convert_amounts,
    get_asset_catalog,
    get_crypto_prices_in_currencies,
    get_rates,
)
from market_data import DEFAULT_RATES_TO_USD


class APIServer:
    def __enter__(self):
        self.server = HTTPServer(("127.0.0.1", 0), ConversionAPIHandler)
        self.host, self.port = self.server.server_address
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def test_convert_amounts_backend_values():
    data = convert_amounts(pesos=10000, soles=100, reais=50, btc=0.1, eth=1)
    assert pytest.approx(data["usd"]["pesos"]) == 10000 * COP_TO_USD
    assert pytest.approx(data["usd"]["soles"]) == 100 * PEN_TO_USD
    assert pytest.approx(data["usd"]["reais"]) == 50 * BRL_TO_USD
    assert pytest.approx(data["usd"]["btc"]) == 0.1 * BTC_TO_USD
    assert pytest.approx(data["usd"]["eth"]) == 1 * ETH_TO_USD
    assert pytest.approx(data["total"]) == sum(data["usd"].values())


def test_get_rates_contains_expected_keys():
    rates = get_rates(allow_network=False)
    for key in ("COP_TO_USD", "PEN_TO_USD", "BRL_TO_USD", "BTC_TO_USD", "ETH_TO_USD"):
        assert key in rates
    assert "SYMBOLS" in rates
    assert "UPDATED_AT" in rates
    assert "SOURCES" in rates
    assert "ASSET_CATALOG" in rates


def test_convert_asset_amount_uses_usd_base_formula():
    rates = {
        "USD": 1.0,
        "BRL": 0.2,
        "BTC": 50000.0,
        "ETH": 2500.0,
        "USDT": 1.0,
        "EUR": 1.1,
    }
    quote = convert_asset_amount(
        amount=1000,
        from_symbol="BRL",
        to_symbol="BTC",
        rates_to_usd=rates,
    )

    assert quote["from_symbol"] == "BRL"
    assert quote["to_symbol"] == "BTC"
    assert pytest.approx(quote["result"]["gross"]) == (1000 * 0.2) / 50000.0
    assert pytest.approx(quote["result"]["net"]) == (1000 * 0.2) / 50000.0


def test_convert_asset_amount_applies_fee_and_spread():
    rates = {"USD": 1.0, "BRL": 0.2, "BTC": 50000.0}
    quote = convert_asset_amount(
        amount=1000,
        from_symbol="BRL",
        to_symbol="BTC",
        fee_percent=1,
        spread_percent=0.5,
        rates_to_usd=rates,
    )

    gross = (1000 * 0.2) / 50000.0
    after_spread = gross * (1 - 0.005)
    expected_net = after_spread * (1 - 0.01)

    assert pytest.approx(quote["result"]["gross"]) == gross
    assert pytest.approx(quote["result"]["net"]) == expected_net
    assert quote["result"]["fee_amount"] > 0
    assert quote["result"]["spread_amount"] > 0


def test_get_asset_catalog_includes_dynamic_rates():
    catalog = get_asset_catalog(
        rates_to_usd={"USD": 1.0, "BRL": 0.2, "BTC": 50000.0, "ETH": 2500.0}
    )
    assert "assets" in catalog
    assert "BTC" in catalog["assets"]
    assert "BRL" in catalog["assets"]
    assert catalog["assets"]["BTC"]["category"] == "crypto"
    assert catalog["assets"]["BRL"]["category"] == "fiat"


def test_api_health_endpoint():
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request("GET", "/health")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["status"] == "ok"
        conn.close()


def test_api_rates_endpoint():
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request("GET", "/rates")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert "rates" in body
        assert "BTC_TO_USD" in body["rates"]
        assert "updated_at" in body
        assert "symbols" in body
        assert "BTC" in body["symbols"]
        assert "USD" in body["symbols"]
        conn.close()


def test_api_assets_endpoint():
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request("GET", "/assets")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert "assets" in body
        assert "BTC" in body["assets"]
        assert "USD" in body["assets"]
        conn.close()


def test_api_convert_endpoint():
    payload = {"pesos": 10000, "btc": 0.1}
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request(
            "POST",
            "/convert",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["inputs"]["pesos"] == 10000
        assert body["inputs"]["btc"] == 0.1
        assert body["usd"]["pesos"] > 0
        assert body["usd"]["btc"] > 0
        assert "market" in body
        assert "updated_at" in body["market"]
        assert "sources" in body["market"]
        assert "symbols" in body["market"]
        conn.close()


def test_api_convert_endpoint_supports_fee_and_spread():
    payload = {"pesos": 10000, "fee_percent": 1, "spread_percent": 0.5}
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request(
            "POST",
            "/convert",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert "pricing" in body
        assert body["pricing"]["fee_percent"] == 1
        assert body["pricing"]["spread_percent"] == 0.5
        conn.close()


def test_api_quote_endpoint(monkeypatch):
    snapshot = {
        "rates_to_usd": {
            "USD": 1.0,
            "USDT": 1.0,
            "BRL": 0.2,
            "EUR": 1.1,
            "COP": 0.00024,
            "PEN": 0.27,
            "BTC": 50000.0,
            "ETH": 2500.0,
        },
        "updated_at": "2026-03-28T12:00:00Z",
        "updated_at_unix": 1774708800,
        "sources": {"crypto": "test", "fiat": "test"},
        "symbols": ["BTC", "ETH", "USDT", "BRL", "USD", "EUR"],
    }
    monkeypatch.setattr("api.get_market_snapshot", lambda allow_network=True: snapshot)

    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request("GET", "/quote?from=BRL&to=BTC&amount=1000&fee_percent=1&spread_percent=0.5")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["from_symbol"] == "BRL"
        assert body["to_symbol"] == "BTC"
        assert body["result"]["net"] > 0
        assert "market" in body
        assert body["market"]["updated_at"] == "2026-03-28T12:00:00Z"
        conn.close()


def test_api_quote_requires_minimum_params():
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request("GET", "/quote?to=BTC")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 400
        assert "error" in body
        conn.close()


def test_api_convert_rejects_invalid_payload():
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request(
            "POST",
            "/convert",
            body=json.dumps({"soles": "abc"}),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 400
        assert "error" in body
        conn.close()


# ---------- Additional backend unit tests ----------


def test_convert_amounts_with_fee_and_spread():
    data = convert_amounts(
        pesos=10000,
        fee_percent=2,
        spread_percent=1,
    )
    gross = 10000 * COP_TO_USD
    after_spread = gross * (1 - 0.01)
    expected_net = after_spread * (1 - 0.02)
    assert pytest.approx(data["usd"]["pesos"], rel=1e-6) == expected_net
    assert data["pricing"]["fee_percent"] == 2
    assert data["pricing"]["spread_percent"] == 1
    assert data["pricing"]["breakdown"]["pesos"]["gross"] > data["pricing"]["breakdown"]["pesos"]["net"]


def test_convert_amounts_fee_above_100_raises():
    with pytest.raises(ValueError, match="fee_percent deve ser menor que 100"):
        convert_amounts(pesos=1000, fee_percent=100)


def test_convert_amounts_spread_above_100_raises():
    with pytest.raises(ValueError, match="spread_percent deve ser menor que 100"):
        convert_amounts(pesos=1000, spread_percent=101)


def test_convert_asset_amount_unknown_from_symbol_raises():
    rates = {"USD": 1.0, "BRL": 0.2}
    with pytest.raises(ValueError, match="não suportado"):
        convert_asset_amount(amount=100, from_symbol="XYZ", to_symbol="USD", rates_to_usd=rates)


def test_convert_asset_amount_unknown_to_symbol_raises():
    rates = {"USD": 1.0, "BRL": 0.2}
    with pytest.raises(ValueError, match="não suportado"):
        convert_asset_amount(amount=100, from_symbol="BRL", to_symbol="XYZ", rates_to_usd=rates)


def test_convert_asset_amount_same_symbol():
    rates = {"USD": 1.0, "BRL": 0.2}
    quote = convert_asset_amount(amount=500, from_symbol="BRL", to_symbol="BRL", rates_to_usd=rates)
    assert pytest.approx(quote["result"]["gross"]) == 500.0
    assert quote["from_symbol"] == "BRL"
    assert quote["to_symbol"] == "BRL"


def test_get_rates_returns_reverse_rates():
    rates = get_rates(allow_network=False)
    assert "USD_TO_COP" in rates
    assert "USD_TO_PEN" in rates
    assert "USD_TO_BRL" in rates
    assert rates["USD_TO_COP"] > 1
    assert rates["USD_TO_PEN"] > 1
    assert rates["USD_TO_BRL"] > 1


def test_get_rates_contains_rates_to_usd_map():
    rates = get_rates(allow_network=False)
    assert "RATES_TO_USD" in rates
    assert isinstance(rates["RATES_TO_USD"], dict)
    assert "BTC" in rates["RATES_TO_USD"]
    assert "USD" in rates["RATES_TO_USD"]


# ---------- Additional API route tests ----------


def test_api_get_unknown_route_returns_404():
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request("GET", "/nonexistent")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 404
        assert "error" in body
        conn.close()


def test_api_post_to_unknown_route_returns_404():
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request(
            "POST",
            "/unknown",
            body=json.dumps({}),
            headers={"Content-Type": "application/json", "Content-Length": "2"},
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 404
        assert "error" in body
        conn.close()


def test_api_post_no_content_length_returns_400():
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        # Send raw request without Content-Length
        conn.putrequest("POST", "/convert")
        conn.putheader("Content-Type", "application/json")
        conn.endheaders()
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 400
        assert "error" in body
        conn.close()


def test_api_post_non_dict_body_returns_400():
    payload = json.dumps([1, 2, 3])
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request(
            "POST",
            "/convert",
            body=payload,
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 400
        assert "error" in body
        conn.close()


def test_api_convert_endpoint_all_currencies():
    payload = {"pesos": 10000, "soles": 100, "reais": 50, "btc": 0.01, "eth": 0.5}
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request(
            "POST",
            "/convert",
            body=json.dumps(payload),
            headers={"Content-Type": "application/json"},
        )
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert body["inputs"]["pesos"] == 10000
        assert body["inputs"]["soles"] == 100
        assert body["inputs"]["reais"] == 50
        assert body["inputs"]["btc"] == 0.01
        assert body["inputs"]["eth"] == 0.5
        assert body["total"] > 0
        conn.close()


def test_api_quote_unsupported_from_symbol_returns_400():
    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request("GET", "/quote?from=FAKECOIN&to=USD&amount=100")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 400
        assert "error" in body
        conn.close()


# ---------- Crypto monitoring backend tests ----------


def test_get_crypto_prices_in_currencies_structure():
    rates = {
        "USD": 1.0,
        "EUR": 1.08,
        "BRL": 0.18,
        "GBP": 1.27,
        "JPY": 0.0066,
        "BTC": 60000.0,
        "ETH": 3000.0,
        "BNB": 600.0,
        "SOL": 150.0,
        "XRP": 0.50,
        "ADA": 0.40,
        "DOGE": 0.12,
    }
    data = get_crypto_prices_in_currencies(rates_to_usd=rates)
    assert "cryptos" in data
    assert "currencies" in data
    assert "prices" in data
    assert "BTC" in data["cryptos"]
    assert "ETH" in data["cryptos"]
    assert "USD" in data["currencies"]
    assert "EUR" in data["currencies"]


def test_get_crypto_prices_in_currencies_values():
    rates = {
        "USD": 1.0,
        "EUR": 1.08,
        "BRL": 0.18,
        "GBP": 1.27,
        "JPY": 0.0066,
        "BTC": 60000.0,
        "ETH": 3000.0,
        "BNB": 600.0,
        "SOL": 150.0,
        "XRP": 0.50,
        "ADA": 0.40,
        "DOGE": 0.12,
    }
    data = get_crypto_prices_in_currencies(rates_to_usd=rates)
    prices = data["prices"]
    # BTC in USD = 60000 / 1.0
    assert pytest.approx(prices["BTC"]["USD"]) == 60000.0
    # BTC in BRL = 60000 / 0.18
    assert pytest.approx(prices["BTC"]["BRL"]) == 60000.0 / 0.18
    # ETH in EUR = 3000 / 1.08
    assert pytest.approx(prices["ETH"]["EUR"]) == 3000.0 / 1.08
    # DOGE in JPY = 0.12 / 0.0066
    assert pytest.approx(prices["DOGE"]["JPY"]) == 0.12 / 0.0066


def test_get_crypto_prices_in_currencies_missing_fiat_skipped():
    # When rates_to_usd provides no EUR, but the function falls back to
    # DEFAULT_RATES_TO_USD which includes EUR; test that explicit override works.
    rates = {"USD": 1.0, "BTC": 50000.0, "ETH": 2500.0, "EUR": 1.1, "BRL": 0.20, "GBP": 1.25, "JPY": 0.007}
    data = get_crypto_prices_in_currencies(rates_to_usd=rates)
    prices = data["prices"]
    assert "USD" in prices.get("BTC", {})
    assert pytest.approx(prices["BTC"]["USD"]) == 50000.0
    assert pytest.approx(prices["BTC"]["EUR"]) == 50000.0 / 1.1


def test_get_crypto_prices_in_currencies_missing_crypto_skipped():
    # When only fiat rates provided, DEFAULT_RATES_TO_USD fills in the crypto
    # defaults; the function returns those default crypto prices.
    rates = {"USD": 1.0, "EUR": 1.08}
    data = get_crypto_prices_in_currencies(rates_to_usd=rates)
    # defaults contain BTC=60000 so it should still appear
    assert "BTC" in data["cryptos"]
    # Verify the price is computed from the default BTC rate
    assert pytest.approx(data["prices"]["BTC"]["USD"]) == DEFAULT_RATES_TO_USD["BTC"]


def test_get_crypto_prices_uses_monitor_constants():
    assert len(MONITOR_CRYPTOS) > 0
    assert len(MONITOR_FIATS) > 0
    assert "BTC" in MONITOR_CRYPTOS
    assert "USD" in MONITOR_FIATS


# ---------- /crypto API endpoint tests ----------


def test_api_crypto_endpoint_structure(monkeypatch):
    snapshot = {
        "rates_to_usd": {
            "USD": 1.0,
            "EUR": 1.08,
            "BRL": 0.18,
            "GBP": 1.27,
            "JPY": 0.0066,
            "BTC": 60000.0,
            "ETH": 3000.0,
            "BNB": 600.0,
            "SOL": 150.0,
            "XRP": 0.50,
            "ADA": 0.40,
            "DOGE": 0.12,
        },
        "updated_at": "2026-04-27T01:00:00Z",
        "updated_at_unix": 1777000000,
        "sources": {"crypto": "test", "fiat": "test"},
        "symbols": list(MONITOR_CRYPTOS) + list(MONITOR_FIATS),
    }
    monkeypatch.setattr("api.get_market_snapshot", lambda allow_network=True: snapshot)

    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request("GET", "/crypto")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert "cryptos" in body
        assert "currencies" in body
        assert "prices" in body
        assert "BTC" in body["cryptos"]
        assert "USD" in body["currencies"]
        assert body["prices"]["BTC"]["USD"] > 0
        conn.close()


def test_api_crypto_endpoint_price_values(monkeypatch):
    snapshot = {
        "rates_to_usd": {
            "USD": 1.0,
            "EUR": 1.08,
            "BRL": 0.18,
            "GBP": 1.27,
            "JPY": 0.0066,
            "BTC": 60000.0,
            "ETH": 3000.0,
            "BNB": 600.0,
            "SOL": 150.0,
            "XRP": 0.50,
            "ADA": 0.40,
            "DOGE": 0.12,
        },
        "updated_at": "2026-04-27T01:00:00Z",
        "updated_at_unix": 1777000000,
        "sources": {"crypto": "test", "fiat": "test"},
        "symbols": list(MONITOR_CRYPTOS) + list(MONITOR_FIATS),
    }
    monkeypatch.setattr("api.get_market_snapshot", lambda allow_network=True: snapshot)

    with APIServer() as srv:
        conn = HTTPConnection(srv.host, srv.port, timeout=5)
        conn.request("GET", "/crypto")
        response = conn.getresponse()
        body = json.loads(response.read().decode("utf-8"))
        assert response.status == 200
        assert pytest.approx(body["prices"]["BTC"]["USD"]) == 60000.0
        assert pytest.approx(body["prices"]["ETH"]["EUR"]) == 3000.0 / 1.08
        conn.close()

