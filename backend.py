"""Core backend logic for currency/crypto conversion."""

from typing import Any, Dict

# Exchange rate constants (1 unit = USD)
COP_TO_USD = 0.00024  # Colombian Peso to USD
PEN_TO_USD = 0.27  # Peruvian Sol to USD
BRL_TO_USD = 0.18  # Brazilian Real to USD
BTC_TO_USD = 60000.00  # Bitcoin to USD
ETH_TO_USD = 3000.00  # Ethereum to USD

# Exchange rate display helpers (1 USD = currency)
USD_TO_COP = 4166.67
USD_TO_PEN = 3.70
USD_TO_BRL = 5.55


def get_rates() -> Dict[str, float]:
    return {
        "COP_TO_USD": COP_TO_USD,
        "PEN_TO_USD": PEN_TO_USD,
        "BRL_TO_USD": BRL_TO_USD,
        "BTC_TO_USD": BTC_TO_USD,
        "ETH_TO_USD": ETH_TO_USD,
        "USD_TO_COP": USD_TO_COP,
        "USD_TO_PEN": USD_TO_PEN,
        "USD_TO_BRL": USD_TO_BRL,
    }


def convert_amounts(
    pesos: Any = 0.0,
    soles: Any = 0.0,
    reais: Any = 0.0,
    btc: Any = 0.0,
    eth: Any = 0.0,
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

    usd_values = {
        "pesos": values["pesos"] * COP_TO_USD,
        "soles": values["soles"] * PEN_TO_USD,
        "reais": values["reais"] * BRL_TO_USD,
        "btc": values["btc"] * BTC_TO_USD,
        "eth": values["eth"] * ETH_TO_USD,
    }
    total = sum(usd_values.values())
    return {"inputs": values, "usd": usd_values, "total": total}
