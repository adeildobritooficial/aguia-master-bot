import os
import time
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, render_template_string


app = Flask(__name__)


APP_NAME = "ÁGUIA MASTER BOT"
APP_MODE = "OBSERVADOR EDUCACIONAL"
APP_VERSION = "1.1.0"

BINANCE_FUTURES_PUBLIC_BASE = "https://fapi.binance.com"
REQUEST_TIMEOUT = 10

WHITE_LIST = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "DOTUSDT",
    "LTCUSDT",
    "TRXUSDT",
    "OPUSDT",
    "ARBUSDT",
    "NEARUSDT",
    "APTUSDT",
    "INJUSDT",
    "SUIUSDT",
    "ATOMUSDT",
    "SEIUSDT",
    "FILUSDT",
    "WLDUSDT",
    "GALAUSDT",
    "UNIUSDT",
]

MAX_ASSETS_TO_ANALYZE = 10


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_round(value, decimals=2):
    try:
        return round(float(value), decimals)
    except Exception:
        return 0


def format_money(value):
    try:
        value = float(value)
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"
        if value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        if value >= 1_000:
            return f"{value / 1_000:.2f}K"
        return f"{value:.2f}"
    except Exception:
        return "0"


def format_price(value):
    try:
        value = float(value)
        if value >= 100:
            return f"{value:.2f}"
        if value >= 1:
            return f"{value:.4f}"
        return f"{value:.6f}"
    except Exception:
        return "N/A"


def binance_get(path, params=None):
    url = f"{BINANCE_FUTURES_PUBLIC_BASE}{path}"

    try:
        response = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as error:
        print(f"Erro ao consultar Binance: {url} | {error}")
        return None


def get_24h_tickers():
    data = binance_get("/fapi/v1/ticker/24hr")

    if not isinstance(data, list):
        return []

    tickers = []

    for item in data:
        symbol = item.get("symbol", "")

        if symbol not in WHITE_LIST:
            continue

        quote_volume = safe_float(item.get("quoteVolume"))
        last_price = safe_float(item.get("lastPrice"))
        change_percent = safe_float(item.get("priceChangePercent"))

        tickers.append(
            {
                "symbol": symbol,
                "quote_volume": quote_volume,
                "last_price": last_price,
                "change_percent": change_percent,
            }
        )

    tickers.sort(key=lambda x: x["quote_volume"], reverse=True)

    return tickers[:MAX_ASSETS_TO_ANALYZE]


def get_klines(symbol, interval, limit=120):
    data = binance_get(
        "/fapi/v1/klines",
        {
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        },
    )

    if not isinstance(data, list):
        return []

    candles = []

    for item in data:
        try:
            candles.append(
                {
                    "open_time": item[0],
                    "open": safe_float(item[1]),
                    "high": safe_float(item[2]),
                    "low": safe_float(item[3]),
                    "close": safe_float(item[4]),
                    "volume": safe_float(item[5]),
                    "close_time": item[6],
                }
            )
        except Exception:
            continue

    return candles


def sma(values, period):
    if len(values) < period:
        return None

    return sum(values[-period:]) / period


def candle_direction(candle):
    if candle["close"] > candle["open"]:
        return "GREEN"

    if candle["close"] < candle["open"]:
        return "RED"

    return "DOJI"


def analyze_trend(candles):
    if len(candles) < 60:
        return {
            "status": "INDEFINIDA",
            "description": "Poucos candles para definir tendência.",
        }

    closes = [c["close"] for c in candles]
    last_close = closes[-1]

    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)

    if sma_20 is None or sma_50 is None:
        return {
            "status": "INDEFINIDA",
            "description": "Médias insuficientes.",
        }

    if last_close > sma_20 > sma_50:
        return {
            "status": "ALTA",
            "description": "Preço acima das médias. Tendência favorece compra.",
        }

    if last_close < sma_20 < sma_50:
        return {
            "status": "BAIXA",
            "description": "Preço abaixo das médias. Tendência favorece venda.",
        }

    return {
        "status": "LATERAL",
        "description": "Mercado sem direção clara. Exige paciência.",
    }


def analyze_levels(candles, lookback=50):
    if not candles:
        return {
            "support": 0,
            "resistance": 0,
            "channel_position": "INDEFINIDA",
            "distance_support_percent": 0,
            "distance_resistance_percent": 0,
        }

    recent = candles[-lookback:] if len(candles) >= lookback else candles

    lows = [c["low"] for c in recent]
    highs = [c["high"] for c in recent]

    support = min(lows)
    resistance = max(highs)
    price = candles[-1]["close"]

    channel_size = resistance - support

    if channel_size <= 0:
        channel_position = "INDEFINIDA"
    else:
        position = (price - support) / channel_size

        if position <= 0.25:
            channel_position = "PERTO DO SUPORTE"
        elif position >= 0.75:
            channel_position = "PERTO DA RESISTÊNCIA"
        else:
            channel_position = "MEIO DO CANAL"

    if price > 0:
        distance_support_percent = ((price - support) / price) * 100
        distance_resistance_percent = ((resistance - price) / price) * 100
    else:
        distance_support_percent = 0
        distance_resistance_percent = 0

    return {
        "support": support,
        "resistance": resistance,
        "channel_position": channel_position,
        "distance_support_percent": safe_round(distance_support_percent, 2),
        "distance_resistance_percent": safe_round(distance_resistance_percent, 2),
    }


def analyze_volume(candles, period=20):
    if len(candles) < period + 1:
        return {
            "status": "INDEFINIDO",
            "ratio": 0,
            "description": "Volume insuficiente.",
        }

    current_volume = candles[-1]["volume"]
    previous = [c["volume"] for c in candles[-period - 1 : -1]]
    average = sum(previous) / len(previous)

    ratio = current_volume / average if average > 0 else 0

    if ratio >= 1.8:
        status = "FORTE"
        description = "Volume acima da média. Existe participação do mercado."
    elif ratio >= 1.2:
        status = "MODERADO"
        description = "Volume melhorando, mas ainda pede confirmação."
    else:
        status = "FRACO"
        description = "Volume fraco. Evitar forçar operação."

    return {
        "status": status,
        "ratio": safe_round(ratio, 2),
        "description": description,
    }


def analyze_candles(candles):
    if len(candles) < 5:
        return {
            "status": "INDEFINIDO",
            "last": "INDEFINIDO",
            "green_count": 0,
            "red_count": 0,
            "rejection": "SEM LEITURA",
            "description": "Poucos candles.",
        }

    last_5 = candles[-5:]
    last_3 = candles[-3:]
    last = candles[-1]

    green_count = sum(1 for c in last_3 if candle_direction(c) == "GREEN")
    red_count = sum(1 for c in last_3 if candle_direction(c) == "RED")

    last_direction = candle_direction(last)

    body = abs(last["close"] - last["open"])
    candle_range = max(last["high"] - last["low"], 0.00000001)

    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]

    if lower_wick > body * 1.5 and lower_wick > candle_range * 0.35:
        rejection = "PAVIO INFERIOR"
    elif upper_wick > body * 1.5 and upper_wick > candle_range * 0.35:
        rejection = "PAVIO SUPERIOR"
    else:
        rejection = "SEM REJEIÇÃO CLARA"

    if green_count >= 2 and last_direction == "GREEN":
        status = "FAVORÁVEL PARA LONG"
        description = "Candles recentes mostram reação compradora."
    elif red_count >= 2 and last_direction == "RED":
        status = "FAVORÁVEL PARA SHORT"
        description = "Candles recentes mostram pressão vendedora."
    else:
        status = "NEUTRO"
        description = "Candles ainda sem confirmação suficiente."

    return {
        "status": status,
        "last": last_direction,
        "green_count": green_count,
        "red_count": red_count,
        "rejection": rejection,
        "description": description,
    }


def analyze_btc_context():
    candles_4h = get_klines("BTCUSDT", "4h", 120)
    candles_5m = get_klines("BTCUSDT", "5m", 120)

    if not candles_4h or not candles_5m:
        return {
            "price": 0,
            "trend_4h": "INDEFINIDA",
            "trend_5m": "INDEFINIDA",
            "pressure": "INDEFINIDA",
            "short_change_percent": 0,
            "message": "Não foi possível ler o BTC.",
        }

    trend_4h = analyze_trend(candles_4h)
    trend_5m = analyze_trend(candles_5m)

    price = candles_5m[-1]["close"]

    recent = candles_5m[-12:]
    first = recent[0]["close"]
    last = recent[-1]["close"]

    short_change = ((last - first) / first) * 100 if first else 0

    if short_change <= -1.0:
        pressure = "VENDEDORA FORTE"
        message = "BTC pressionando para baixo. Cuidado com Long contra o fluxo."
    elif short_change >= 1.0:
        pressure = "COMPRADORA FORTE"
        message = "BTC pressionando para cima. Cuidado com Short contra o fluxo."
    else:
        pressure = "LATERAL"
        message = "BTC sem pressão extrema neste momento."

    return {
        "price": price,
        "trend_4h": trend_4h["status"],
        "trend_5m": trend_5m["status"],
        "pressure": pressure,
        "short_change_percent": safe_round(short_change, 2),
        "message": message,
    }


def decide_direction(trend_4h, trend_5m, levels_5m, volume, candles, btc_context):
    long_points = 0
    short_points = 0
    reasons = []
    blocks = []

    if trend_4h["status"] in ["ALTA", "LATERAL"]:
        long_points += 1
    else:
        blocks.append("4H não favorece Long.")

    if trend_4h["status"] in ["BAIXA", "LATERAL"]:
        short_points += 1
    else:
        blocks.append("4H não favorece Short.")

    if trend_5m["status"] == "ALTA":
        long_points += 2
        reasons.append("5M com estrutura de alta.")
    elif trend_5m["status"] == "BAIXA":
        short_points += 2
        reasons.append("5M com estrutura de baixa.")
    else:
        reasons.append("5M lateral ou indefinido.")

    if candles["status"] == "FAVORÁVEL PARA LONG":
        long_points += 2
        reasons.append("Candles favorecem Long.")

    if candles["status"] == "FAVORÁVEL PARA SHORT":
        short_points += 2
        reasons.append("Candles favorecem Short.")

    if candles["rejection"] == "PAVIO INFERIOR":
        long_points += 1
        reasons.append("Pavio inferior indica defesa de suporte.")

    if candles["rejection"] == "PAVIO SUPERIOR":
        short_points += 1
        reasons.append("Pavio superior indica rejeição na resistência.")

    if levels_5m["channel_position"] == "PERTO DO SUPORTE":
        long_points += 1
        reasons.append("Preço próximo ao suporte.")
    elif levels_5m["channel_position"] == "PERTO DA RESISTÊNCIA":
        short_points += 1
        reasons.append("Preço próximo à resistência.")
    else:
        blocks.append("Preço no meio do canal.")

    if volume["status"] == "FORTE":
        long_points += 1
        short_points += 1
        reasons.append("Volume forte.")
    elif volume["status"] == "MODERADO":
        reasons.append("Volume moderado.")
    else:
        blocks.append("Volume fraco.")

    if btc_context["pressure"] == "VENDEDORA FORTE":
        long_points -= 2
        short_points += 1
        blocks.append("BTC com pressão vendedora forte.")
    elif btc_context["pressure"] == "COMPRADORA FORTE":
        short_points -= 2
        long_points += 1
        blocks.append("BTC com pressão compradora forte.")

    if long_points >= short_points + 2 and long_points >= 5:
        direction = "POSSÍVEL LONG"
    elif short_points >= long_points + 2 and short_points >= 5:
        direction = "POSSÍVEL SHORT"
    else:
        direction = "NONE"

    return {
        "direction": direction,
        "long_points": long_points,
        "short_points": short_points,
        "reasons": reasons,
        "blocks": blocks,
    }


def calculate_score(direction_data, trend_4h, trend_5m, levels_5m, volume, candles, btc_context):
    score = 0
    hard_blocks = []
    warnings = []

    direction = direction_data["direction"]

    if trend_4h["status"] in ["ALTA", "BAIXA"]:
        score += 10
    elif trend_4h["status"] == "LATERAL":
        score += 5
        warnings.append("4H lateral. Exige mais confirmação no 5M.")

    if trend_5m["status"] in ["ALTA", "BAIXA"]:
        score += 15
    else:
        warnings.append("5M sem direção forte.")

    if candles["status"] in ["FAVORÁVEL PARA LONG", "FAVORÁVEL PARA SHORT"]:
        score += 20
    else:
        hard_blocks.append("Candles sem confirmação.")

    if candles["rejection"] in ["PAVIO INFERIOR", "PAVIO SUPERIOR"]:
        score += 10

    if volume["status"] == "FORTE":
        score += 20
    elif volume["status"] == "MODERADO":
        score += 10
        warnings.append("Volume moderado. Aguardar confirmação.")
    else:
        hard_blocks.append("Volume fraco.")

    if levels_5m["channel_position"] in ["PERTO DO SUPORTE", "PERTO DA RESISTÊNCIA"]:
        score += 15
    else:
        hard_blocks.append("Preço no meio do canal.")

    if btc_context["pressure"] in ["COMPRADORA FORTE", "VENDEDORA FORTE"]:
        warnings.append("BTC com pressão forte. Cautela elevada.")
        score -= 10

    if direction == "NONE":
        hard_blocks.append("Sem direção operacional clara.")
        score = min(score, 45)

    if hard_blocks:
        score = min(score, 69)

    score = max(0, min(100, int(score)))

    if score >= 80:
        label = "SETUP FORTE EDUCACIONAL"
    elif score >= 70:
        label = "SETUP MODERADO"
    elif score >= 50:
        label = "SETUP EM FORMAÇÃO"
    else:
        label = "AGUARDAR"

    return {
        "score": score,
        "label": label,
        "hard_blocks": hard_blocks,
        "warnings": warnings,
    }


def classify_setup_phase(score_data, direction_data, levels_5m, volume, candles):
    score = score_data["score"]
    direction = direction_data["direction"]

    if direction != "NONE" and score >= 70 and not score_data["hard_blocks"]:
        return {
            "phase": "POSSÍVEL SETUP EDUCACIONAL",
            "action": "Observar confirmação final. Nenhuma ordem automática.",
            "color": "green",
        }

    if score >= 50:
        if volume["status"] in ["FORTE", "MODERADO"] or candles["status"] != "NEUTRO":
            return {
                "phase": "SETUP EM FORMAÇÃO",
                "action": "Monitorar reteste, rompimento ou confirmação de volume.",
                "color": "yellow",
            }

    if levels_5m["channel_position"] == "MEIO DO CANAL":
        return {
            "phase": "MEIO DO CANAL",
            "action": "Aguardar aproximação de suporte ou resistência.",
            "color": "red",
        }

    return {
        "phase": "SEM SETUP",
        "action": "Preservar capital e aguardar nova estrutura.",
        "color": "gray",
    }


def build_risk_engine(score_data, direction_data, btc_context):
    score = score_data["score"]
    direction = direction_data["direction"]
    hard_blocks = score_data["hard_blocks"]

    if direction == "NONE":
        return {
            "status": "NÃO OPERAR",
            "risk": "BAIXO/MÉDIO",
            "message": "Sem direção operacional clara. Robô permanece observando.",
        }

    if hard_blocks:
        return {
            "status": "BLOQUEADO",
            "risk": "MÉDIO",
            "message": "Existem travas técnicas. Aguardar nova confirmação.",
        }

    if btc_context["pressure"] in ["COMPRADORA FORTE", "VENDEDORA FORTE"]:
        return {
            "status": "CAUTELA MÁXIMA",
            "risk": "ALTO",
            "message": "BTC está com pressão forte. Evitar decisão precipitada.",
        }

    if score >= 80:
        return {
            "status": "OBSERVAR SETUP",
            "risk": "MÉDIO",
            "message": "Setup forte para estudo, mas sem execução automática.",
        }

    if score >= 70:
        return {
            "status": "MONITORAR COM CAUTELA",
            "risk": "MÉDIO",
            "message": "Setup moderado. Exige confirmação adicional.",
        }

    return {
        "status": "AGUARDAR",
        "risk": "BAIXO",
        "message": "Score insuficiente para cenário educacional.",
    }


def build_educational_3x(score_data, direction_data):
    score = score_data["score"]
    direction = direction_data["direction"]

    if direction == "NONE":
        return {
            "status": "3X BLOQUEADO",
            "message": "Sem direção técnica clara. 3X não deve ser considerado.",
            "reduce_only": "SIM, obrigatório em saída parcial.",
        }

    if score < 80:
        return {
            "status": "3X BLOQUEADO",
            "message": "Score abaixo do nível mínimo educacional para estudar 3X.",
            "reduce_only": "SIM, obrigatório em saída parcial.",
        }

    if score_data["hard_blocks"]:
        return {
            "status": "3X BLOQUEADO",
            "message": "Existem bloqueios técnicos. Não estudar 3X neste cenário.",
            "reduce_only": "SIM, obrigatório em saída parcial.",
        }

    return {
        "status": "3X SOMENTE EDUCACIONAL",
        "message": "Cenário pode ser observado em estudo, sem execução automática.",
        "reduce_only": "SIM, obrigatório em saída parcial.",
    }


def analyze_asset(ticker, btc_context):
    symbol = ticker["symbol"]

    candles_4h = get_klines(symbol, "4h", 120)
    candles_5m = get_klines(symbol, "5m", 120)

    if not candles_4h or not candles_5m:
        return {
            "symbol": symbol,
            "status": "ERRO",
            "message": "Dados insuficientes.",
            "score": 0,
        }

    price = candles_5m[-1]["close"]

    trend_4h = analyze_trend(candles_4h)
    trend_5m = analyze_trend(candles_5m)

    levels_4h = analyze_levels(candles_4h, 50)
    levels_5m = analyze_levels(candles_5m, 40)

    volume = analyze_volume(candles_5m)
    candles = analyze_candles(candles_5m)

    direction_data = decide_direction(
        trend_4h,
        trend_5m,
        levels_5m,
        volume,
        candles,
        btc_context,
    )

    score_data = calculate_score(
        direction_data,
        trend_4h,
        trend_5m,
        levels_5m,
        volume,
        candles,
        btc_context,
    )

    setup_phase = classify_setup_phase(
        score_data,
        direction_data,
        levels_5m,
        volume,
        candles,
    )

    risk_engine = build_risk_engine(score_data, direction_data, btc_context)

    educational_3x = build_educational_3x(score_data, direction_data)

    return {
        "symbol": symbol,
        "status": "OK",
        "price": price,
        "change_percent": ticker["change_percent"],
        "quote_volume": ticker["quote_volume"],
        "trend_4h": trend_4h,
        "trend_5m": trend_5m,
        "levels_4h": levels_4h,
        "levels_5m": levels_5m,
        "volume": volume,
        "candles": candles,
        "direction": direction_data["direction"],
        "long_points": direction_data["long_points"],
        "short_points": direction_data["short_points"],
        "reasons": direction_data["reasons"],
        "blocks": direction_data["blocks"],
        "score": score_data["score"],
        "score_label": score_data["label"],
        "hard_blocks": score_data["hard_blocks"],
        "warnings": score_data["warnings"],
        "setup_phase": setup_phase,
        "risk_engine": risk_engine,
        "educational_3x": educational_3x,
    }


def build_general_decision(assets, btc_context):
    valid_assets = [a for a in assets if a.get("status") == "OK"]

    possible_setups = [
        a
        for a in valid_assets
        if a["setup_phase"]["phase"] == "POSSÍVEL SETUP EDUCACIONAL"
    ]

    forming_setups = [
        a
        for a in valid_assets
        if a["setup_phase"]["phase"] == "SETUP EM FORMAÇÃO"
    ]

    if btc_context["pressure"] in ["COMPRADORA FORTE", "VENDEDORA FORTE"]:
        return {
            "status": "CAUTELA MÁXIMA",
            "reason": "BTC está com pressão forte no curto prazo.",
            "action": "Não forçar entrada. Aguardar estabilização ou confirmação clara.",
            "color": "red",
        }

    if possible_setups:
        best = sorted(possible_setups, key=lambda x: x["score"], reverse=True)[0]

        return {
            "status": "OBSERVAR SETUP",
            "reason": f"{best['symbol']} apresenta confluência educacional, mas sem execução automática.",
            "action": "Aguardar confirmação humana, reteste e validação de risco.",
            "color": "green",
        }

    if forming_setups:
        best = sorted(forming_setups, key=lambda x: x["score"], reverse=True)[0]

        return {
            "status": "SETUP EM FORMAÇÃO",
            "reason": f"{best['symbol']} está formando cenário, mas ainda não confirmou.",
            "action": "Monitorar volume, candle de confirmação e posição no canal.",
            "color": "yellow",
        }

    return {
        "status": "NÃO OPERAR",
        "reason": "Nenhuma oportunidade operacional forte encontrada neste ciclo.",
        "action": "Preservar capital. Não operar no meio do canal, sem direção ou sem volume.",
        "color": "red",
    }


def build_report():
    started = time.time()

    btc_context = analyze_btc_context()
    tickers = get_24h_tickers()

    assets = []

    for ticker in tickers:
        asset = analyze_asset(ticker, btc_context)
        assets.append(asset)

    valid_assets = [a for a in assets if a.get("status") == "OK"]

    top_opportunities = sorted(
        valid_assets,
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:5]

    setup_radar = [
        a
        for a in valid_assets
        if a["setup_phase"]["phase"] in [
            "POSSÍVEL SETUP EDUCACIONAL",
            "SETUP EM FORMAÇÃO",
            "MEIO DO CANAL",
        ]
    ]

    setup_radar = sorted(
        setup_radar,
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:7]

    general_decision = build_general_decision(valid_assets, btc_context)

    possible_longs = len([a for a in valid_assets if a.get("direction") == "POSSÍVEL LONG"])
    possible_shorts = len([a for a in valid_assets if a.get("direction") == "POSSÍVEL SHORT"])
    waiting = len([a for a in valid_assets if a.get("direction") == "NONE"])

    duration = round(time.time() - started, 2)

    summary = {
        "app_name": APP_NAME,
        "mode": APP_MODE,
        "version": APP_VERSION,
        "updated_at": now_utc(),
        "selection_mode": "AUTO_VOLUME_WITH_WHITE_LIST",
        "white_list_enabled": True,
        "white_list_count": len(WHITE_LIST),
        "assets_analyzed": len(valid_assets),
        "possible_longs": possible_longs,
        "possible_shorts": possible_shorts,
        "waiting": waiting,
        "duration_seconds": duration,
        "orders_enabled": False,
        "real_orders_enabled": False,
        "testnet_orders_enabled": False,
    }

    return {
        "summary": summary,
        "general_decision": general_decision,
        "btc_context": btc_context,
        "top_opportunities": top_opportunities,
        "setup_radar": setup_radar,
        "assets": valid_assets,
    }


HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>ÁGUIA MASTER BOT</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>
        body {
            margin: 0;
            background: #0b1020;
            color: #f8fafc;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 16px;
        }

        .page {
            max-width: 1180px;
            margin: auto;
            padding: 36px 18px 60px;
        }

        h1 {
            font-size: 38px;
            margin-bottom: 8px;
        }

        h2 {
            font-size: 26px;
            margin-top: 0;
        }

        h3 {
            font-size: 20px;
            margin-bottom: 8px;
        }

        p {
            line-height: 1.5;
        }

        .subtitle {
            color: #cbd5e1;
            font-size: 18px;
        }

        .card {
            background: #1e293b;
            border-radius: 18px;
            padding: 24px;
            margin: 22px 0;
            box-shadow: 0 12px 30px rgba(0,0,0,0.22);
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 14px;
        }

        .box {
            background: #0f172a;
            border-radius: 12px;
            padding: 14px;
            overflow: hidden;
        }

        .col-3 {
            grid-column: span 3;
        }

        .col-4 {
            grid-column: span 4;
        }

        .col-6 {
            grid-column: span 6;
        }

        .col-12 {
            grid-column: span 12;
        }

        .pill {
            display: inline-block;
            border-radius: 999px;
            padding: 8px 12px;
            margin: 4px 4px 4px 0;
            background: #0f172a;
            color: #e2e8f0;
            font-weight: bold;
            font-size: 14px;
        }

        .green {
            background: #16a34a;
            color: white;
        }

        .yellow {
            background: #f59e0b;
            color: #111827;
        }

        .red {
            background: #ef4444;
            color: white;
        }

        .gray {
            background: #64748b;
            color: white;
        }

        .blue {
            background: #2563eb;
            color: white;
        }

        .border-green {
            border-left: 7px solid #16a34a;
        }

        .border-yellow {
            border-left: 7px solid #f59e0b;
        }

        .border-red {
            border-left: 7px solid #ef4444;
        }

        .border-gray {
            border-left: 7px solid #64748b;
        }

        .muted {
            color: #94a3b8;
        }

        .alert {
            background: rgba(239,68,68,0.15);
            border: 1px solid rgba(239,68,68,0.35);
            color: #fecaca;
            padding: 14px;
            border-radius: 12px;
            margin-top: 12px;
        }

        .note {
            background: rgba(59,130,246,0.15);
            border: 1px solid rgba(59,130,246,0.35);
            color: #bfdbfe;
            padding: 14px;
            border-radius: 12px;
            margin-top: 12px;
        }

        .asset {
            background: #1e293b;
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 16px;
        }

        .asset-title {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
        }

        .score {
            font-size: 26px;
            font-weight: 900;
        }

        .list-item {
            margin: 6px 0;
        }

        a {
            color: #93c5fd;
        }

        @media (max-width: 900px) {
            .col-3,
            .col-4,
            .col-6 {
                grid-column: span 12;
            }

            h1 {
                font-size: 30px;
            }

            h2 {
                font-size: 22px;
            }

            body {
                font-size: 15px;
            }
        }
    </style>
</head>

<body>
    <div class="page">

        <h1>🦅 ÁGUIA MASTER BOT</h1>
        <p class="subtitle">
            Robô observador do Método Águia Cripto — modo seguro, educacional e sem execução de ordens.
        </p>
        <p class="muted">Última atualização: {{ summary.updated_at }}</p>

        <div class="card">
            <h2>Resumo do Ciclo</h2>

            <div class="grid">
                <div class="box col-3">
                    <strong>Modo seleção:</strong><br>
                    {{ summary.selection_mode }}
                </div>

                <div class="box col-3">
                    <strong>Lista branca:</strong><br>
                    {{ summary.white_list_enabled }}
                </div>

                <div class="box col-3">
                    <strong>Ativos analisados:</strong><br>
                    {{ summary.assets_analyzed }}
                </div>

                <div class="box col-3">
                    <strong>Duração:</strong><br>
                    {{ summary.duration_seconds }}s
                </div>

                <div class="box col-3">
                    <strong>Possíveis Longs:</strong><br>
                    {{ summary.possible_longs }}
                </div>

                <div class="box col-3">
                    <strong>Possíveis Shorts:</strong><br>
                    {{ summary.possible_shorts }}
                </div>

                <div class="box col-3">
                    <strong>Aguardando:</strong><br>
                    {{ summary.waiting }}
                </div>

                <div class="box col-3">
                    <strong>Versão:</strong><br>
                    {{ summary.version }}
                </div>
            </div>
        </div>

        <div class="card border-{{ general_decision.color }}">
            <h2>Decisão Geral do Ciclo</h2>

            <span class="pill {{ general_decision.color }}">
                {{ general_decision.status }}
            </span>

            <p><strong>Motivo:</strong> {{ general_decision.reason }}</p>
            <p><strong>Ação recomendada:</strong> {{ general_decision.action }}</p>

            <p class="muted">
                Regra de segurança: este robô está em modo observador.
                Nenhuma ordem real ou testnet é executada automaticamente.
            </p>
        </div>

        <div class="card">
            <h2>Contexto BTC</h2>

            <div class="grid">
                <div class="box col-3">
                    <strong>Preço:</strong><br>
                    {{ btc_context.price | price }}
                </div>

                <div class="box col-3">
                    <strong>4H:</strong><br>
                    {{ btc_context.trend_4h }}
                </div>

                <div class="box col-3">
                    <strong>5M:</strong><br>
                    {{ btc_context.trend_5m }}
                </div>

                <div class="box col-3">
                    <strong>Pressão:</strong><br>
                    {{ btc_context.pressure }}
                </div>

                <div class="box col-3">
                    <strong>Variação curta:</strong><br>
                    {{ btc_context.short_change_percent }}%
                </div>
            </div>

            <p>{{ btc_context.message }}</p>
        </div>

        <div class="card">
            <h2>Radar de Setup em Formação</h2>
            <p class="muted">
                Este bloco mostra ativos que ainda não são operação, mas que merecem observação.
            </p>

            {% if setup_radar %}
                {% for item in setup_radar %}
                    <div class="asset border-{{ item.setup_phase.color }}">
                        <div class="asset-title">
                            <h3>{{ item.symbol }}</h3>
                            <span class="pill {{ item.setup_phase.color }}">
                                {{ item.setup_phase.phase }}
                            </span>
                        </div>

                        <span class="pill blue">Score: {{ item.score }}</span>
                        <span class="pill">Direção: {{ item.direction }}</span>
                        <span class="pill">Canal 5M: {{ item.levels_5m.channel_position }}</span>
                        <span class="pill">Volume: {{ item.volume.status }} — {{ item.volume.ratio }}x</span>
                        <span class="pill">Candles: {{ item.candles.status }}</span>

                        <p><strong>Ação:</strong> {{ item.setup_phase.action }}</p>

                        {% if item.warnings %}
                            <p><strong>Alertas:</strong></p>
                            {% for warning in item.warnings %}
                                <div class="list-item">⚠️ {{ warning }}</div>
                            {% endfor %}
                        {% endif %}
                    </div>
                {% endfor %}
            {% else %}
                <div class="note">
                    Nenhum setup em formação encontrado neste ciclo.
                </div>
            {% endif %}
        </div>

        <div class="card">
            <h2>Top Oportunidades do Ciclo</h2>

            {% if top_opportunities %}
                {% for item in top_opportunities %}
                    <div class="asset">
                        <div class="asset-title">
                            <h3>#{{ loop.index }} {{ item.symbol }}</h3>
                            <span class="pill {{ item.setup_phase.color }}">
                                {{ item.setup_phase.phase }}
                            </span>
                        </div>

                        <span class="pill blue">Score: {{ item.score }}</span>
                        <span class="pill">Preço: {{ item.price | price }}</span>
                        <span class="pill">Direção: {{ item.direction }}</span>
                        <span class="pill">Confiança: {{ item.score_label }}</span>
                        <span class="pill">Volume 24h: {{ item.quote_volume | money }}</span>

                        <p><strong>Leitura:</strong> {{ item.setup_phase.action }}</p>

                        {% if item.hard_blocks %}
                            <p><strong>Pontos de atenção:</strong></p>
                            {% for block in item.hard_blocks %}
                                <div class="list-item">⛔ {{ block }}</div>
                            {% endfor %}
                        {% endif %}

                        {% if item.warnings %}
                            <p><strong>Travazinhas de segurança:</strong></p>
                            {% for warning in item.warnings %}
                                <div class="list-item">⚠️ {{ warning }}</div>
                            {% endfor %}
                        {% endif %}
                    </div>
                {% endfor %}
            {% else %}
                <div class="note">
                    Nenhuma oportunidade encontrada neste ciclo.
                </div>
            {% endif %}
        </div>

        <div class="card">
            <h2>Análise dos Ativos</h2>

            {% for item in assets %}
                <div class="asset">
                    <div class="asset-title">
                        <h3>{{ item.symbol }}</h3>
                        <span class="pill {{ item.setup_phase.color }}">
                            {{ item.setup_phase.phase }}
                        </span>
                    </div>

                    <span class="pill">Preço: {{ item.price | price }}</span>
                    <span class="pill">Score: {{ item.score }}</span>
                    <span class="pill">Direção: {{ item.direction }}</span>
                    <span class="pill">4H: {{ item.trend_4h.status }}</span>
                    <span class="pill">5M: {{ item.trend_5m.status }}</span>
                    <span class="pill">Volume: {{ item.volume.status }}</span>
                    <span class="pill">Canal 5M: {{ item.levels_5m.channel_position }}</span>

                    <div class="grid">
                        <div class="box col-6">
                            <h3>4H — Contexto</h3>
                            <p><strong>Tendência:</strong> {{ item.trend_4h.status }}</p>
                            <p>{{ item.trend_4h.description }}</p>
                            <p><strong>Suporte:</strong> {{ item.levels_4h.support | price }}</p>
                            <p><strong>Resistência:</strong> {{ item.levels_4h.resistance | price }}</p>
                        </div>

                        <div class="box col-6">
                            <h3>5M — Gatilho</h3>
                            <p><strong>Tendência:</strong> {{ item.trend_5m.status }}</p>
                            <p><strong>Candles:</strong> {{ item.candles.status }}</p>
                            <p><strong>Rejeição:</strong> {{ item.candles.rejection }}</p>
                            <p><strong>Volume:</strong> {{ item.volume.status }} — {{ item.volume.ratio }}x</p>
                        </div>
                    </div>

                    {% if item.reasons %}
                        <p><strong>Motivos positivos:</strong></p>
                        {% for reason in item.reasons %}
                            <div class="list-item">✅ {{ reason }}</div>
                        {% endfor %}
                    {% endif %}

                    {% if item.blocks %}
                        <p><strong>Bloqueios:</strong></p>
                        {% for block in item.blocks %}
                            <div class="list-item">⛔ {{ block }}</div>
                        {% endfor %}
                    {% endif %}

                    <div class="note">
                        <strong>Motor de Risco Educacional:</strong>
                        {{ item.risk_engine.status }} —
                        {{ item.risk_engine.risk }} —
                        {{ item.risk_engine.message }}
                    </div>

                    <div class="alert">
                        <strong>3X Educacional:</strong>
                        {{ item.educational_3x.status }} —
                        {{ item.educational_3x.message }}
                        <br>
                        <strong>Reduce Only:</strong> {{ item.educational_3x.reduce_only }}
                    </div>
                </div>
            {% endfor %}
        </div>

        <div class="card">
            <h2>Segurança Operacional</h2>

            <p>
                Este painel é apenas educacional. Ele não envia ordem, não usa chave de API,
                não acessa saldo, não altera posições e não executa compra ou venda.
            </p>

            <div class="alert">
                Regra central: preservar capital vem antes de qualquer oportunidade.
            </div>
        </div>

        <p class="muted">
            Links rápidos:
            <a href="/api/report">API JSON</a> |
            <a href="/health">Health</a> |
            <a href="/dashboard">Dashboard</a>
        </p>

    </div>
</body>
</html>
"""


@app.template_filter("money")
def money_filter(value):
    return format_money(value)


@app.template_filter("price")
def price_filter(value):
    return format_price(value)


@app.route("/")
def home():
    return """
    <html>
        <head>
            <meta charset="UTF-8">
            <title>ÁGUIA MASTER BOT</title>
            <style>
                body {
                    background: #0b1020;
                    color: white;
                    font-family: Arial, sans-serif;
                    padding: 40px;
                }

                a {
                    color: #93c5fd;
                    font-size: 20px;
                }
            </style>
        </head>

        <body>
            <h1>🦅 ÁGUIA MASTER BOT</h1>
            <p>Robô observador educacional online.</p>
            <p><a href="/dashboard">Abrir Dashboard</a></p>
            <p><a href="/api/report">Ver API JSON</a></p>
            <p><a href="/health">Ver Health</a></p>
        </body>
    </html>
    """


@app.route("/dashboard")
def dashboard():
    report = build_report()

    return render_template_string(
        HTML,
        summary=report["summary"],
        general_decision=report["general_decision"],
        btc_context=report["btc_context"],
        top_opportunities=report["top_opportunities"],
        setup_radar=report["setup_radar"],
        assets=report["assets"],
    )


@app.route("/api/report")
def api_report():
    return jsonify(build_report())


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "app": APP_NAME,
            "mode": APP_MODE,
            "version": APP_VERSION,
            "orders_enabled": False,
            "real_orders_enabled": False,
            "testnet_orders_enabled": False,
            "updated_at": now_utc(),
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)