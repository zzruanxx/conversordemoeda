"""Simple HTTP API for currency conversion."""

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

from backend import (
    convert_amounts,
    convert_asset_amount,
    get_asset_catalog,
    get_market_snapshot,
    get_rates,
)


class ConversionAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path

        if route == "/health":
            self._send_json({"status": "ok"})
            return
        if route == "/rates":
            rates = get_rates(allow_network=True)
            self._send_json(
                {
                    "rates": rates,
                    "updated_at": rates.get("UPDATED_AT"),
                    "symbols": rates.get("SYMBOLS", []),
                    "sources": rates.get("SOURCES", {}),
                }
            )
            return
        if route == "/assets":
            catalog = get_asset_catalog(allow_network=True)
            self._send_json(catalog)
            return
        if route == "/quote":
            params = parse_qs(parsed.query)
            from_symbol = params.get("from", [None])[0]
            to_symbol = params.get("to", ["USD"])[0]
            amount = params.get("amount", [None])[0]
            fee_percent = params.get("fee_percent", ["0"])[0]
            spread_percent = params.get("spread_percent", ["0"])[0]

            if not from_symbol or amount is None:
                self._send_json(
                    {
                        "error": "Required query params: from, amount. Optional: to, fee_percent, spread_percent"
                    },
                    status=HTTPStatus.BAD_REQUEST,
                )
                return

            try:
                snapshot = get_market_snapshot(allow_network=True)
                quote = convert_asset_amount(
                    amount=amount,
                    from_symbol=from_symbol,
                    to_symbol=to_symbol,
                    fee_percent=fee_percent,
                    spread_percent=spread_percent,
                    rates_to_usd=snapshot.get("rates_to_usd", {}),
                )
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                return

            quote["market"] = {
                "updated_at": snapshot.get("updated_at"),
                "sources": snapshot.get("sources", {}),
                "symbols": snapshot.get("symbols", []),
            }
            self._send_json(quote)
            return
        self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/convert":
            self._send_json({"error": "Not Found"}, status=HTTPStatus.NOT_FOUND)
            return

        content_length = self.headers.get("Content-Length")
        if content_length is None:
            self._send_json(
                {"error": "Content-Length header is required"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            raw = self.rfile.read(int(content_length))
            data = json.loads(raw.decode("utf-8"))
        except (ValueError, json.JSONDecodeError):
            self._send_json({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
            return

        if not isinstance(data, dict):
            self._send_json(
                {"error": "JSON body must be an object"},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            snapshot = get_market_snapshot(allow_network=True)
            result = convert_amounts(
                pesos=data.get("pesos", 0),
                soles=data.get("soles", 0),
                reais=data.get("reais", 0),
                btc=data.get("btc", 0),
                eth=data.get("eth", 0),
                rates_to_usd=snapshot.get("rates_to_usd", {}),
                fee_percent=data.get("fee_percent", 0),
                spread_percent=data.get("spread_percent", 0),
            )
            result["market"] = {
                "updated_at": snapshot.get("updated_at"),
                "sources": snapshot.get("sources", {}),
                "symbols": snapshot.get("symbols", []),
            }
        except ValueError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json(result, status=HTTPStatus.OK)

    def log_message(self, format: str, *args: Any) -> None:
        return


def run_api(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = HTTPServer((host, port), ConversionAPIHandler)
    print(f"API running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run_api()
