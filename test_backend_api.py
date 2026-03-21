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
    convert_amounts,
    get_rates,
)


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
    rates = get_rates()
    for key in ("COP_TO_USD", "PEN_TO_USD", "BRL_TO_USD", "BTC_TO_USD", "ETH_TO_USD"):
        assert key in rates


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
        assert pytest.approx(body["usd"]["pesos"]) == 10000 * COP_TO_USD
        assert pytest.approx(body["usd"]["btc"]) == 0.1 * BTC_TO_USD
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
