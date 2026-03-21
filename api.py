"""Simple HTTP API for currency conversion."""

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Dict

from backend import convert_amounts, get_rates


class ConversionAPIHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: Dict[str, Any], status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json({"status": "ok"})
            return
        if self.path == "/rates":
            self._send_json({"rates": get_rates()})
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
            result = convert_amounts(
                pesos=data.get("pesos", 0),
                soles=data.get("soles", 0),
                reais=data.get("reais", 0),
                btc=data.get("btc", 0),
                eth=data.get("eth", 0),
            )
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
