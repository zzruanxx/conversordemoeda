"""Core backend logic for currency/crypto conversion."""

from typing import Any, Dict

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


def get_market_snapshot(
    force_refresh: bool = False,
    allow_network: bool = True,
) -> Dict[str, object]:
    """Get market snapshot with standardized symbols, timestamp and source metadata."""
    return _MARKET_DATA.get_snapshot(force_refresh=force_refresh, allow_network=allow_network)


def get_rates(allow_network: bool = True) -> Dict[str, Any]:
    snapshot = get_market_snapshot(allow_network=allow_network)
    rates_to_usd = snapshot.get("rates_to_usd", {})

    def _rate(symbol: str, fallback: float) -> float:
        raw = rates_to_usd.get(normalize_symbol(symbol), fallback)
        try:
            value = float(raw)
        except (TypeError, ValueError):
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
            **DEFAULT_RATES_TO_USD,
            **{k: float(v) for k, v in rates_to_usd.items() if isinstance(v, (int, float))},
        },
        "UPDATED_AT": snapshot.get("updated_at"),
        "UPDATED_AT_UNIX": snapshot.get("updated_at_unix"),
        "SOURCES": snapshot.get("sources", {}),
    }


def convert_amounts(
    pesos: Any = 0.0,
    soles: Any = 0.0,
    reais: Any = 0.0,
    btc: Any = 0.0,
    eth: Any = 0.0,
    rates_to_usd: Dict[str, float] | None = None,
) -> Dict[str, Dict[str, float] | float]:
    fields = {
        "pesos": ("Pesos Colombianos (COP)", pesos),
        "soles": ("Soles Peruanos (PEN)", soles),
        "reais": ("Reais Brasileiros (BRL)", reais),
        "btc": ("Bitcoin (BTC)", btc),
        "eth": ("Ethereum (ETH)", eth),
    }
    values: Dict[str, float] = {}
    for key, (name, raw) in fields.items():
        try:
            numeric = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Valor inválido '{raw}' para {name}") from exc
        if numeric < 0:
            raise ValueError(f"Valor negativo {numeric} não permitido para {name}")
        values[key] = numeric

    mapping = rates_to_usd or {}
    cop_to_usd = float(mapping.get("COP", COP_TO_USD))
    pen_to_usd = float(mapping.get("PEN", PEN_TO_USD))
    brl_to_usd = float(mapping.get("BRL", BRL_TO_USD))
    btc_to_usd = float(mapping.get("BTC", BTC_TO_USD))
    eth_to_usd = float(mapping.get("ETH", ETH_TO_USD))

    usd_values = {
        "pesos": values["pesos"] * cop_to_usd,
        "soles": values["soles"] * pen_to_usd,
        "reais": values["reais"] * brl_to_usd,
        "btc": values["btc"] * btc_to_usd,
        "eth": values["eth"] * eth_to_usd,
    }
    total = sum(usd_values.values())
    return {"inputs": values, "usd": usd_values, "total": total}
