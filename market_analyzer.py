# market_analyzer.py

import pandas as pd


def get_last_candle(df: pd.DataFrame) -> dict:
    """
    Retorna informações do último candle fechado.
    """
    last = df.iloc[-1]

    direction = "GREEN" if last["close"] > last["open"] else "RED" if last["close"] < last["open"] else "DOJI"

    body_size = abs(last["close"] - last["open"])
    full_range = last["high"] - last["low"]

    body_percent = 0
    if full_range > 0:
        body_percent = (body_size / full_range) * 100

    return {
        "open": float(last["open"]),
        "high": float(last["high"]),
        "low": float(last["low"]),
        "close": float(last["close"]),
        "volume": float(last["volume"]),
        "direction": direction,
        "body_percent": round(body_percent, 2),
    }


def analyze_volume(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    Compara volume atual com média dos candles anteriores.
    """
    recent = df.tail(lookback)
    current_volume = float(df.iloc[-1]["volume"])
    avg_volume = float(recent["volume"].mean())

    if current_volume > avg_volume * 1.25:
        status = "HIGH"
    elif current_volume < avg_volume * 0.75:
        status = "LOW"
    else:
        status = "NORMAL"

    return {
        "current_volume": round(current_volume, 4),
        "avg_volume": round(avg_volume, 4),
        "status": status,
    }


def find_support_resistance(df: pd.DataFrame, lookback: int = 40) -> dict:
    """
    Calcula suporte e resistência simples com base em máximas e mínimas recentes.
    Esta é uma versão inicial e será evoluída depois.
    """
    recent = df.tail(lookback)

    support = float(recent["low"].min())
    resistance = float(recent["high"].max())
    current_price = float(df.iloc[-1]["close"])

    distance_to_support = ((current_price - support) / current_price) * 100
    distance_to_resistance = ((resistance - current_price) / current_price) * 100

    return {
        "support": round(support, 4),
        "resistance": round(resistance, 4),
        "current_price": round(current_price, 4),
        "distance_to_support_percent": round(distance_to_support, 2),
        "distance_to_resistance_percent": round(distance_to_resistance, 2),
    }


def analyze_market_structure(df_4h: pd.DataFrame, df_5m: pd.DataFrame) -> dict:
    """
    Faz uma leitura inicial da estrutura de mercado.
    """
    last_4h = get_last_candle(df_4h)
    last_5m = get_last_candle(df_5m)

    volume_5m = analyze_volume(df_5m)
    sr_4h = find_support_resistance(df_4h)

    near_support = sr_4h["distance_to_support_percent"] <= 2.0
    near_resistance = sr_4h["distance_to_resistance_percent"] <= 2.0

    return {
        "last_4h_candle": last_4h,
        "last_5m_candle": last_5m,
        "volume_5m": volume_5m,
        "support_resistance_4h": sr_4h,
        "near_support": near_support,
        "near_resistance": near_resistance,
    }