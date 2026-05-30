# exchange_binance.py

import requests
import pandas as pd


BINANCE_PUBLIC_BASE_URL = "https://testnet.binancefuture.com"


def get_klines(symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
    """
    Consulta candles públicos da Binance Futures Demo/Testnet.
    Nesta fase não usa API Key e não executa ordens.
    """
    url = f"{BINANCE_PUBLIC_BASE_URL}/fapi/v1/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()

    columns = [
        "open_time",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
        "ignore",
    ]

    df = pd.DataFrame(data, columns=columns)

    numeric_columns = [
        "open",
        "high",
        "low",
        "close",
        "volume",
        "quote_asset_volume",
        "taker_buy_base_volume",
        "taker_buy_quote_volume",
    ]

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")

    return df


def get_current_price(symbol: str) -> float:
    """
    Consulta preço atual público da Binance Futures Demo/Testnet.
    """
    url = f"{BINANCE_PUBLIC_BASE_URL}/fapi/v1/ticker/price"

    params = {
        "symbol": symbol,
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()

    data = response.json()
    return float(data["price"])