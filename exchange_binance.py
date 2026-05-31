# exchange_binance.py

import requests
import pandas as pd


BINANCE_PUBLIC_BASE_URL = "https://testnet.binancefuture.com"


def get_klines(symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
    """
    Consulta candles públicos da Binance Futures Testnet.
    Nesta fase não usa API Key e não executa ordens.
    """
    url = f"{BINANCE_PUBLIC_BASE_URL}/fapi/v1/klines"

    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    response = requests.get(url, params=params, timeout=15)
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
    Consulta preço atual público da Binance Futures Testnet.
    """
    url = f"{BINANCE_PUBLIC_BASE_URL}/fapi/v1/ticker/price"

    params = {
        "symbol": symbol,
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    data = response.json()
    return float(data["price"])


def get_top_usdt_symbols(limit: int = 10) -> list[str]:
    """
    Busca automaticamente os principais pares USDT Futures por volume.

    Nesta fase usa dados públicos da Binance Futures Testnet.
    Se falhar, o main.py usa FALLBACK_SYMBOLS.
    """
    url = f"{BINANCE_PUBLIC_BASE_URL}/fapi/v1/ticker/24hr"

    response = requests.get(url, timeout=20)
    response.raise_for_status()

    data = response.json()

    blocked_keywords = [
        "USDC",
        "BUSD",
        "TUSD",
        "FDUSD",
    ]

    candidates = []

    for item in data:
        symbol = item.get("symbol", "")

        if not symbol.endswith("USDT"):
            continue

        if any(blocked in symbol for blocked in blocked_keywords):
            continue

        try:
            quote_volume = float(item.get("quoteVolume", 0))
        except ValueError:
            quote_volume = 0

        if quote_volume <= 0:
            continue

        candidates.append(
            {
                "symbol": symbol,
                "quote_volume": quote_volume,
            }
        )

    candidates = sorted(
        candidates,
        key=lambda x: x["quote_volume"],
        reverse=True,
    )

    top_symbols = [item["symbol"] for item in candidates[:limit]]

    # Garantir BTC e ETH sempre na análise
    for required in ["ETHUSDT", "BTCUSDT"]:
        if required not in top_symbols:
            top_symbols.insert(0, required)

    # Remover duplicados mantendo ordem
    unique_symbols = []

    for symbol in top_symbols:
        if symbol not in unique_symbols:
            unique_symbols.append(symbol)

    return unique_symbols[:limit]