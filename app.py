import os
import time
import math
import statistics
from datetime import datetime, timezone

import requests
from flask import Flask, render_template_string, jsonify


app = Flask(__name__)


# ============================================================
# ÁGUIA MASTER BOT
# Modo: Observador Educacional
# Ambiente: Binance Futures Testnet / Dados Públicos
# Importante: este arquivo NÃO executa ordens.
# ============================================================


APP_NAME = "ÁGUIA MASTER BOT"
APP_MODE = "OBSERVADOR EDUCACIONAL"
VERSION = "1.0.0"

BINANCE_FUTURES_PUBLIC_BASE = "https://fapi.binance.com"
BINANCE_FUTURES_TESTNET_BASE = "https://testnet.binancefuture.com"

USE_TESTNET_PUBLIC = os.getenv("USE_TESTNET_PUBLIC", "false").lower() == "true"

BASE_URL = BINANCE_FUTURES_TESTNET_BASE if USE_TESTNET_PUBLIC else BINANCE_FUTURES_PUBLIC_BASE


# Lista branca operacional.
# O robô só analisa ativos presentes aqui.
WHITE_LIST = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT",
    "XRPUSDT",
    "ADAUSDT",
    "DOGEUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "MATICUSDT",
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
]


MAX_SYMBOLS_BY_VOLUME = 12
REQUEST_TIMEOUT = 8


# ============================================================
# Utilidades
# ============================================================


def now_utc_text():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def safe_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def safe_percent(value):
    try:
        return round(float(value), 2)
    except Exception:
        return 0.0


def format_price(value):
    try:
        value = float(value)
        if value >= 100:
            return f"{value:,.2f}"
        if value >= 1:
            return f"{value:,.4f}"
        return f"{value:,.6f}"
    except Exception:
        return "N/A"


def request_json(path, params=None):
    url = f"{BASE_URL}{path}"
    try:
        response = requests.get(url, params=params or {}, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as error:
        print(f"[ERRO REQUEST] {url} -> {error}")
        return None


# ============================================================
# Binance Dados Públicos
# ============================================================


def get_24h_tickers():
    data = request_json("/fapi/v1/ticker/24hr")
    if isinstance(data, list):
        return data
    return []


def get_klines(symbol, interval="5m", limit=120):
    data = request_json(
        "/fapi/v1/klines",
        params={
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


def get_symbols_by_volume():
    tickers = get_24h_tickers()

    filtered = []

    for ticker in tickers:
        symbol = ticker.get("symbol", "")

        if symbol not in WHITE_LIST:
            continue

        quote_volume = safe_float(ticker.get("quoteVolume", 0))
        price_change_percent = safe_float(ticker.get("priceChangePercent", 0))
        last_price = safe_float(ticker.get("lastPrice", 0))

        filtered.append(
            {
                "symbol": symbol,
                "quote_volume": quote_volume,
                "price_change_percent": price_change_percent,
                "last_price": last_price,
            }
        )

    filtered.sort(key=lambda x: x["quote_volume"], reverse=True)

    return filtered[:MAX_SYMBOLS_BY_VOLUME]


# ============================================================
# Indicadores Técnicos Simples
# ============================================================


def calculate_sma(values, period):
    if not values or len(values) < period:
        return None

    return sum(values[-period:]) / period


def calculate_support_resistance(candles, lookback=40):
    if not candles:
        return {
            "support": None,
            "resistance": None,
        }

    recent = candles[-lookback:] if len(candles) >= lookback else candles

    lows = [c["low"] for c in recent]
    highs = [c["high"] for c in recent]

    support = min(lows) if lows else None
    resistance = max(highs) if highs else None

    return {
        "support": support,
        "resistance": resistance,
    }


def calculate_volume_context(candles, period=20):
    if not candles or len(candles) < period + 1:
        return {
            "current_volume": 0,
            "average_volume": 0,
            "volume_ratio": 0,
            "status": "DADOS INSUFICIENTES",
        }

    current_volume = candles[-1]["volume"]
    previous_volumes = [c["volume"] for c in candles[-period - 1 : -1]]
    average_volume = sum(previous_volumes) / len(previous_volumes)

    if average_volume <= 0:
        volume_ratio = 0
    else:
        volume_ratio = current_volume / average_volume

    if volume_ratio >= 1.8:
        status = "VOLUME FORTE"
    elif volume_ratio >= 1.2:
        status = "VOLUME MODERADO"
    else:
        status = "VOLUME FRACO"

    return {
        "current_volume": current_volume,
        "average_volume": average_volume,
        "volume_ratio": round(volume_ratio, 2),
        "status": status,
    }


def analyze_last_candles(candles):
    if not candles or len(candles) < 3:
        return {
            "status": "DADOS INSUFICIENTES",
            "bullish_count": 0,
            "bearish_count": 0,
            "last_candle_direction": "NEUTRO",
        }

    last_three = candles[-3:]
    bullish_count = 0
    bearish_count = 0

    for candle in last_three:
        if candle["close"] > candle["open"]:
            bullish_count += 1
        elif candle["close"] < candle["open"]:
            bearish_count += 1

    last = candles[-1]

    if last["close"] > last["open"]:
        last_candle_direction = "ALTA"
    elif last["close"] < last["open"]:
        last_candle_direction = "BAIXA"
    else:
        last_candle_direction = "NEUTRO"

    body = abs(last["close"] - last["open"])
    total_range = max(last["high"] - last["low"], 0.00000001)
    body_ratio = body / total_range

    lower_wick = min(last["open"], last["close"]) - last["low"]
    upper_wick = last["high"] - max(last["open"], last["close"])

    rejection = "SEM REJEIÇÃO CLARA"

    if lower_wick > body * 1.5:
        rejection = "REJEIÇÃO INFERIOR"
    elif upper_wick > body * 1.5:
        rejection = "REJEIÇÃO SUPERIOR"

    if bullish_count >= 2 and last_candle_direction == "ALTA":
        status = "CANDLES FAVORÁVEIS PARA LONG"
    elif bearish_count >= 2 and last_candle_direction == "BAIXA":
        status = "CANDLES FAVORÁVEIS PARA SHORT"
    else:
        status = "CANDLES NEUTROS"

    return {
        "status": status,
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "last_candle_direction": last_candle_direction,
        "body_ratio": round(body_ratio, 2),
        "rejection": rejection,
    }


def analyze_trend(candles):
    if not candles or len(candles) < 60:
        return {
            "trend": "INDEFINIDA",
            "description": "Dados insuficientes para tendência.",
        }

    closes = [c["close"] for c in candles]

    sma_20 = calculate_sma(closes, 20)
    sma_50 = calculate_sma(closes, 50)
    last_close = closes[-1]

    if sma_20 is None or sma_50 is None:
        return {
            "trend": "INDEFINIDA",
            "description": "Médias insuficientes.",
        }

    if last_close > sma_20 > sma_50:
        return {
            "trend": "ALTA",
            "description": "Preço acima das médias principais.",
        }

    if last_close < sma_20 < sma_50:
        return {
            "trend": "BAIXA",
            "description": "Preço abaixo das médias principais.",
        }

    return {
        "trend": "LATERAL",
        "description": "Mercado sem direção forte.",
    }


def calculate_distance_to_levels(price, support, resistance):
    if not price:
        return {
            "distance_to_support_percent": 0,
            "distance_to_resistance_percent": 0,
        }

    if support:
        distance_to_support = ((price - support) / price) * 100
    else:
        distance_to_support = 0

    if resistance:
        distance_to_resistance = ((resistance - price) / price) * 100
    else:
        distance_to_resistance = 0

    return {
        "distance_to_support_percent": round(distance_to_support, 2),
        "distance_to_resistance_percent": round(distance_to_resistance, 2),
    }


# ============================================================
# Contexto BTC
# ============================================================


def analyze_btc_context():
    candles_4h = get_klines("BTCUSDT", "4h", 120)
    candles_5m = get_klines("BTCUSDT", "5m", 120)

    if not candles_4h or not candles_5m:
        return {
            "symbol": "BTCUSDT",
            "status": "DADOS INSUFICIENTES",
            "trend_4h": "INDEFINIDA",
            "trend_5m": "INDEFINIDA",
            "pressure": "NEUTRA",
            "risk_message": "Não foi possível ler dados suficientes do BTC.",
            "last_price": 0,
        }

    trend_4h = analyze_trend(candles_4h)
    trend_5m = analyze_trend(candles_5m)

    last_price = candles_5m[-1]["close"]

    recent_closes = [c["close"] for c in candles_5m[-12:]]
    first = recent_closes[0]
    last = recent_closes[-1]

    short_change = ((last - first) / first) * 100 if first else 0

    if short_change <= -1.0:
        pressure = "PRESSÃO VENDEDORA FORTE"
        risk_message = "BTC caindo forte no curto prazo. Evitar novas entradas compradas sem confirmação."
    elif short_change >= 1.0:
        pressure = "PRESSÃO COMPRADORA FORTE"
        risk_message = "BTC subindo forte no curto prazo. Cuidado com Shorts contra o fluxo."
    else:
        pressure = "NEUTRA/LATERAL"
        risk_message = "BTC sem pressão extrema no curto prazo."

    return {
        "symbol": "BTCUSDT",
        "status": "OK",
        "trend_4h": trend_4h["trend"],
        "trend_5m": trend_5m["trend"],
        "pressure": pressure,
        "risk_message": risk_message,
        "last_price": last_price,
        "short_change_percent": round(short_change, 2),
    }


# ============================================================
# Estratégia MEC Educacional
# ============================================================


def decide_direction(analysis_4h, analysis_5m, volume_5m, candles_5m, btc_context):
    trend_4h = analysis_4h["trend"]["trend"]
    trend_5m = analysis_5m["trend"]["trend"]
    candle_status = analysis_5m["candles"]["status"]
    rejection = analysis_5m["candles"]["rejection"]
    volume_status = volume_5m["status"]
    btc_pressure = btc_context.get("pressure", "NEUTRA")

    long_points = 0
    short_points = 0
    reasons = []

    if trend_4h in ["ALTA", "LATERAL"]:
        long_points += 1
        reasons.append("4H não está contra Long.")

    if trend_4h in ["BAIXA", "LATERAL"]:
        short_points += 1
        reasons.append("4H não está contra Short.")

    if trend_5m == "ALTA":
        long_points += 2
        reasons.append("5M favorece Long.")

    if trend_5m == "BAIXA":
        short_points += 2
        reasons.append("5M favorece Short.")

    if candle_status == "CANDLES FAVORÁVEIS PARA LONG":
        long_points += 2
        reasons.append("Candles recentes favorecem Long.")

    if candle_status == "CANDLES FAVORÁVEIS PARA SHORT":
        short_points += 2
        reasons.append("Candles recentes favorecem Short.")

    if rejection == "REJEIÇÃO INFERIOR":
        long_points += 1
        reasons.append("Rejeição inferior pode indicar defesa de suporte.")

    if rejection == "REJEIÇÃO SUPERIOR":
        short_points += 1
        reasons.append("Rejeição superior pode indicar defesa de resistência.")

    if volume_status in ["VOLUME FORTE", "VOLUME MODERADO"]:
        long_points += 1
        short_points += 1
        reasons.append("Volume tem participação relevante.")

    if btc_pressure == "PRESSÃO VENDEDORA FORTE":
        long_points -= 2
        short_points += 1
        reasons.append("BTC com pressão vendedora forte.")

    if btc_pressure == "PRESSÃO COMPRADORA FORTE":
        short_points -= 2
        long_points += 1
        reasons.append("BTC com pressão compradora forte.")

    if long_points >= short_points + 2 and long_points >= 4:
        direction = "LONG"
    elif short_points >= long_points + 2 and short_points >= 4:
        direction = "SHORT"
    else:
        direction = "SEM DIREÇÃO"

    return {
        "direction": direction,
        "long_points": long_points,
        "short_points": short_points,
        "reasons": reasons,
    }


def calculate_score(symbol, ticker_data, analysis_4h, analysis_5m, direction_data, btc_context):
    score = 0
    blocks = []
    alerts = []

    direction = direction_data["direction"]
    trend_4h = analysis_4h["trend"]["trend"]
    trend_5m = analysis_5m["trend"]["trend"]
    volume_status = analysis_5m["volume"]["status"]
    volume_ratio = analysis_5m["volume"]["volume_ratio"]
    candle_status = analysis_5m["candles"]["status"]
    rejection = analysis_5m["candles"]["rejection"]
    btc_pressure = btc_context.get("pressure", "NEUTRA/LATERAL")

    quote_volume = ticker_data.get("quote_volume", 0)

    if quote_volume >= 500_000_000:
        score += 15
    elif quote_volume >= 100_000_000:
        score += 10
    elif quote_volume >= 30_000_000:
        score += 5
    else:
        blocks.append("Volume 24h baixo para prioridade operacional.")

    if direction == "LONG":
        if trend_4h in ["ALTA", "LATERAL"]:
            score += 15
        else:
            blocks.append("4H contra Long.")

        if trend_5m == "ALTA":
            score += 15
        else:
            blocks.append("5M ainda não confirma Long.")

        if candle_status == "CANDLES FAVORÁVEIS PARA LONG":
            score += 15
        else:
            blocks.append("Candles não confirmam Long.")

        if rejection == "REJEIÇÃO INFERIOR":
            score += 10

        if btc_pressure == "PRESSÃO VENDEDORA FORTE":
            score -= 20
            blocks.append("BTC contra entrada Long.")

    elif direction == "SHORT":
        if trend_4h in ["BAIXA", "LATERAL"]:
            score += 15
        else:
            blocks.append("4H contra Short.")

        if trend_5m == "BAIXA":
            score += 15
        else:
            blocks.append("5M ainda não confirma Short.")

        if candle_status == "CANDLES FAVORÁVEIS PARA SHORT":
            score += 15
        else:
            blocks.append("Candles não confirmam Short.")

        if rejection == "REJEIÇÃO SUPERIOR":
            score += 10

        if btc_pressure == "PRESSÃO COMPRADORA FORTE":
            score -= 20
            blocks.append("BTC contra entrada Short.")

    else:
        blocks.append("Sem direção técnica clara.")
        score = min(score, 35)

    if volume_status == "VOLUME FORTE":
        score += 15
    elif volume_status == "VOLUME MODERADO":
        score += 8
    else:
        blocks.append("Volume 5M fraco.")
        score = min(score, 60)

    if volume_ratio < 1.0:
        alerts.append("Volume atual abaixo da média recente.")

    # Travas rígidas
    if direction == "SEM DIREÇÃO":
        score = min(score, 35)

    if volume_status == "VOLUME FRACO":
        score = min(score, 60)

    if candle_status == "CANDLES NEUTROS":
        score = min(score, 65)

    if blocks:
        score = min(score, 75)

    score = max(0, min(100, int(score)))

    if score >= 80:
        classification = "FORTE, MAS SOMENTE OBSERVAR"
    elif score >= 60:
        classification = "MODERADA / MONITORAR"
    elif score >= 40:
        classification = "FRACA / AGUARDAR"
    else:
        classification = "SEM OPORTUNIDADE"

    return {
        "score": score,
        "classification": classification,
        "blocks": blocks,
        "alerts": alerts,
    }


def build_risk_engine(score_data, direction_data, btc_context):
    score = score_data["score"]
    direction = direction_data["direction"]
    blocks = score_data["blocks"]
    btc_pressure = btc_context.get("pressure", "NEUTRA/LATERAL")

    decision = "AGUARDAR"
    risk_level = "BAIXO"
    message = "Cenário sem liberação operacional. Apenas observar."

    if direction == "SEM DIREÇÃO":
        decision = "BLOQUEAR"
        risk_level = "MÉDIO"
        message = "Sem direção técnica clara. Entrada bloqueada no modo educacional."

    elif blocks:
        decision = "AGUARDAR"
        risk_level = "MÉDIO"
        message = "Existem bloqueios técnicos. Aguardar novas confirmações."

    elif score >= 80:
        decision = "OBSERVAR COM ATENÇÃO"
        risk_level = "MÉDIO"
        message = "Boa confluência técnica, mas o robô segue sem executar ordens."

    elif score >= 60:
        decision = "MONITORAR"
        risk_level = "MÉDIO"
        message = "Cenário parcial. Precisa de confirmação adicional."

    else:
        decision = "AGUARDAR"
        risk_level = "BAIXO"
        message = "Score insuficiente para qualquer consideração operacional."

    if btc_pressure in ["PRESSÃO VENDEDORA FORTE", "PRESSÃO COMPRADORA FORTE"]:
        risk_level = "ALTO"
        message += " Atenção: BTC está com pressão forte no curto prazo."

    return {
        "decision": decision,
        "risk_level": risk_level,
        "message": message,
    }


def build_educational_3x(symbol, direction, analysis_5m, score_data):
    score = score_data["score"]

    if direction == "SEM DIREÇÃO":
        return {
            "status": "NÃO CONSIDERAR 3X",
            "message": "Sem direção técnica clara. 3X educacional bloqueado.",
            "reduce_only": "OBRIGATÓRIO EM SAÍDA PARCIAL",
            "suggestion": "Aguardar estrutura melhor.",
        }

    if score < 70:
        return {
            "status": "NÃO CONSIDERAR 3X",
            "message": "Score insuficiente para cenário educacional de 3X.",
            "reduce_only": "OBRIGATÓRIO EM SAÍDA PARCIAL",
            "suggestion": "Aguardar confluência mais forte.",
        }

    volume_status = analysis_5m["volume"]["status"]
    candle_status = analysis_5m["candles"]["status"]

    if volume_status == "VOLUME FRACO" or candle_status == "CANDLES NEUTROS":
        return {
            "status": "3X BLOQUEADO",
            "message": "Volume ou candles não confirmam força suficiente.",
            "reduce_only": "OBRIGATÓRIO EM SAÍDA PARCIAL",
            "suggestion": "Aguardar confirmação.",
        }

    return {
        "status": "3X APENAS EDUCACIONAL",
        "message": f"{symbol} tem confluência técnica para estudo, mas sem execução automática.",
        "reduce_only": "OBRIGATÓRIO EM SAÍDA PARCIAL",
        "suggestion": "Em ambiente real, exigir autorização humana e gestão rígida.",
    }


# ============================================================
# Análise dos Ativos
# ============================================================


def analyze_symbol(ticker_data, btc_context):
    symbol = ticker_data["symbol"]

    candles_4h = get_klines(symbol, "4h", 120)
    candles_5m = get_klines(symbol, "5m", 120)

    if not candles_4h or not candles_5m:
        return {
            "symbol": symbol,
            "status": "ERRO",
            "message": "Dados insuficientes.",
            "score": 0,
            "direction": "SEM DIREÇÃO",
        }

    price = candles_5m[-1]["close"]

    levels_4h = calculate_support_resistance(candles_4h, 50)
    levels_5m = calculate_support_resistance(candles_5m, 40)

    distance_4h = calculate_distance_to_levels(
        price,
        levels_4h["support"],
        levels_4h["resistance"],
    )

    distance_5m = calculate_distance_to_levels(
        price,
        levels_5m["support"],
        levels_5m["resistance"],
    )

    analysis_4h = {
        "trend": analyze_trend(candles_4h),
        "levels": levels_4h,
        "distance": distance_4h,
    }

    analysis_5m = {
        "trend": analyze_trend(candles_5m),
        "levels": levels_5m,
        "distance": distance_5m,
        "volume": calculate_volume_context(candles_5m),
        "candles": analyze_last_candles(candles_5m),
    }

    direction_data = decide_direction(
        analysis_4h,
        analysis_5m,
        analysis_5m["volume"],
        candles_5m,
        btc_context,
    )

    score_data = calculate_score(
        symbol,
        ticker_data,
        analysis_4h,
        analysis_5m,
        direction_data,
        btc_context,
    )

    risk_engine = build_risk_engine(score_data, direction_data, btc_context)

    educational_3x = build_educational_3x(
        symbol,
        direction_data["direction"],
        analysis_5m,
        score_data,
    )

    return {
        "symbol": symbol,
        "status": "OK",
        "last_price": price,
        "quote_volume": ticker_data.get("quote_volume", 0),
        "price_change_percent": ticker_data.get("price_change_percent", 0),
        "direction": direction_data["direction"],
        "long_points": direction_data["long_points"],
        "short_points": direction_data["short_points"],
        "reasons": direction_data["reasons"],
        "score": score_data["score"],
        "classification": score_data["classification"],
        "blocks": score_data["blocks"],
        "alerts": score_data["alerts"],
        "analysis_4h": analysis_4h,
        "analysis_5m": analysis_5m,
        "risk_engine": risk_engine,
        "educational_3x": educational_3x,
    }


def build_general_decision(top_opportunities, btc_context):
    if not top_opportunities:
        return {
            "status": "AGUARDAR",
            "message": "Nenhuma oportunidade relevante foi encontrada neste ciclo.",
            "level": "BAIXO",
            "color": "gray",
        }

    best = top_opportunities[0]

    best_symbol = best.get("symbol", "N/A")
    best_score = best.get("score", 0)
    best_direction = best.get("direction", "SEM DIREÇÃO")
    best_blocks = best.get("blocks", [])
    btc_pressure = btc_context.get("pressure", "NEUTRA/LATERAL")

    if best_direction == "SEM DIREÇÃO":
        return {
            "status": "AGUARDAR",
            "message": "O melhor ativo do ciclo ainda não possui direção técnica clara.",
            "level": "BAIXO",
            "color": "gray",
        }

    if btc_pressure in ["PRESSÃO VENDEDORA FORTE", "PRESSÃO COMPRADORA FORTE"]:
        return {
            "status": "CAUTELA MÁXIMA",
            "message": f"{best_symbol} apareceu no ranking, mas o BTC está com pressão forte. O robô permanece apenas observando.",
            "level": "ALTO",
            "color": "red",
        }

    if best_blocks:
        return {
            "status": "MONITORAR",
            "message": f"{best_symbol} tem sinais parciais, mas ainda possui bloqueios técnicos.",
            "level": "MÉDIO",
            "color": "yellow",
        }

    if best_score >= 80:
        return {
            "status": "ATENÇÃO OPERACIONAL EDUCACIONAL",
            "message": f"{best_symbol} apresenta boa confluência para {best_direction}, mas nenhuma ordem será executada.",
            "level": "MÉDIO/ALTO",
            "color": "green",
        }

    if best_score >= 60:
        return {
            "status": "MONITORAR",
            "message": f"{best_symbol} apresenta sinais moderados. Aguardar confirmação adicional.",
            "level": "MÉDIO",
            "color": "yellow",
        }

    return {
        "status": "AGUARDAR",
        "message": "Nenhuma oportunidade possui confluência técnica suficiente neste ciclo.",
        "level": "BAIXO",
        "color": "gray",
    }


def build_cycle_report():
    started_at = time.time()

    btc_context = analyze_btc_context()

    symbols_by_volume = get_symbols_by_volume()

    assets_analysis = []

    for ticker_data in symbols_by_volume:
        analysis = analyze_symbol(ticker_data, btc_context)
        assets_analysis.append(analysis)

    valid_assets = [a for a in assets_analysis if a.get("status") == "OK"]

    top_opportunities = sorted(
        valid_assets,
        key=lambda x: x.get("score", 0),
        reverse=True,
    )[:5]

    general_decision = build_general_decision(top_opportunities, btc_context)

    if top_opportunities:
        best = top_opportunities[0]
        best_symbol = best.get("symbol", "N/A")
        best_score = best.get("score", 0)
        best_direction = best.get("direction", "SEM DIREÇÃO")
    else:
        best_symbol = "N/A"
        best_score = 0
        best_direction = "SEM DIREÇÃO"

    finished_at = time.time()
    duration = round(finished_at - started_at, 2)

    summary = {
        "app_name": APP_NAME,
        "mode": APP_MODE,
        "version": VERSION,
        "environment": "Binance Futures Testnet / Dados Públicos",
        "base_url": BASE_URL,
        "cycle_time": now_utc_text(),
        "duration_seconds": duration,
        "white_list_count": len(WHITE_LIST),
        "analyzed_count": len(valid_assets),
        "best_symbol": best_symbol,
        "best_score": best_score,
        "best_direction": best_direction,
        "orders_enabled": False,
        "real_trading_enabled": False,
        "testnet_trading_enabled": False,
    }

    return {
        "summary": summary,
        "general_decision": general_decision,
        "btc_context": btc_context,
        "top_opportunities": top_opportunities,
        "assets_analysis": assets_analysis,
    }


# ============================================================
# HTML Dashboard
# ============================================================


DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>ÁGUIA MASTER BOT</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <style>
        body {
            margin: 0;
            padding: 0;
            background: #0b1020;
            color: #e5e7eb;
            font-family: Arial, Helvetica, sans-serif;
        }

        .container {
            max-width: 1300px;
            margin: 0 auto;
            padding: 24px;
        }

        .header {
            background: linear-gradient(135deg, #111827, #1e3a8a);
            border-radius: 18px;
            padding: 26px;
            margin-bottom: 22px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.35);
        }

        .header h1 {
            margin: 0 0 8px 0;
            font-size: 34px;
            color: #ffffff;
        }

        .header p {
            margin: 4px 0;
            color: #cbd5e1;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 18px;
        }

        .card {
            background: #111827;
            border: 1px solid #1f2937;
            border-radius: 16px;
            padding: 20px;
            box-shadow: 0 10px 22px rgba(0,0,0,0.25);
        }

        .card h2 {
            margin-top: 0;
            margin-bottom: 14px;
            color: #ffffff;
            font-size: 22px;
        }

        .card h3 {
            margin-top: 0;
            color: #f9fafb;
        }

        .col-12 {
            grid-column: span 12;
        }

        .col-6 {
            grid-column: span 6;
        }

        .col-4 {
            grid-column: span 4;
        }

        .status-green {
            border-left: 6px solid #22c55e;
        }

        .status-yellow {
            border-left: 6px solid #eab308;
        }

        .status-red {
            border-left: 6px solid #ef4444;
        }

        .status-gray {
            border-left: 6px solid #64748b;
        }

        .pill {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            background: #1f2937;
            color: #e5e7eb;
            font-size: 13px;
            margin: 3px 4px 3px 0;
        }

        .pill-green {
            background: rgba(34,197,94,0.15);
            color: #86efac;
            border: 1px solid rgba(34,197,94,0.35);
        }

        .pill-yellow {
            background: rgba(234,179,8,0.15);
            color: #fde68a;
            border: 1px solid rgba(234,179,8,0.35);
        }

        .pill-red {
            background: rgba(239,68,68,0.15);
            color: #fca5a5;
            border: 1px solid rgba(239,68,68,0.35);
        }

        .pill-blue {
            background: rgba(59,130,246,0.15);
            color: #93c5fd;
            border: 1px solid rgba(59,130,246,0.35);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            overflow: hidden;
            border-radius: 12px;
        }

        th, td {
            padding: 12px 10px;
            border-bottom: 1px solid #1f2937;
            text-align: left;
            font-size: 14px;
        }

        th {
            color: #cbd5e1;
            background: #0f172a;
        }

        tr:hover {
            background: rgba(255,255,255,0.03);
        }

        .muted {
            color: #94a3b8;
        }

        .small {
            font-size: 13px;
        }

        .score {
            font-size: 24px;
            font-weight: bold;
        }

        .warning {
            background: rgba(239,68,68,0.12);
            border: 1px solid rgba(239,68,68,0.35);
            padding: 12px;
            border-radius: 12px;
            color: #fecaca;
        }

        .success {
            background: rgba(34,197,94,0.12);
            border: 1px solid rgba(34,197,94,0.35);
            padding: 12px;
            border-radius: 12px;
            color: #bbf7d0;
        }

        .info {
            background: rgba(59,130,246,0.12);
            border: 1px solid rgba(59,130,246,0.35);
            padding: 12px;
            border-radius: 12px;
            color: #bfdbfe;
        }

        @media (max-width: 900px) {
            .col-6, .col-4 {
                grid-column: span 12;
            }

            .header h1 {
                font-size: 26px;
            }

            table {
                font-size: 12px;
            }

            th, td {
                padding: 8px 6px;
            }
        }
    </style>
</head>

<body>
    <div class="container">

        <div class="header">
            <h1>🦅 ÁGUIA MASTER BOT</h1>
            <p><strong>Modo:</strong> {{ summary.mode }}</p>
            <p><strong>Ambiente:</strong> {{ summary.environment }}</p>
            <p><strong>Importante:</strong> robô observador, sem execução de ordens reais ou testnet.</p>
        </div>

        <div class="grid">

            <div class="card col-12">
                <h2>Resumo do Ciclo</h2>
                <span class="pill pill-blue">Versão: {{ summary.version }}</span>
                <span class="pill pill-blue">Horário: {{ summary.cycle_time }}</span>
                <span class="pill pill-blue">Duração: {{ summary.duration_seconds }}s</span>
                <span class="pill pill-blue">Ativos analisados: {{ summary.analyzed_count }}</span>
                <span class="pill pill-blue">Lista branca: {{ summary.white_list_count }}</span>

                <p></p>

                <p><strong>Melhor ativo:</strong> {{ summary.best_symbol }}</p>
                <p><strong>Melhor direção:</strong> {{ summary.best_direction }}</p>
                <p><strong>Melhor score:</strong> {{ summary.best_score }}</p>

                <div class="warning">
                    Execução de ordens: DESATIVADA. API Key: NÃO USADA. Modo apenas educacional e observador.
                </div>
            </div>

            <div class="card col-12 status-{{ general_decision.color }}">
                <h2>Decisão Geral do Ciclo</h2>
                <p><strong>Status:</strong> {{ general_decision.status }}</p>
                <p><strong>Mensagem:</strong> {{ general_decision.message }}</p>
                <p><strong>Nível:</strong> {{ general_decision.level }}</p>
            </div>

            <div class="card col-12">
                <h2>Contexto BTC</h2>
                <span class="pill pill-blue">BTCUSDT</span>
                <span class="pill">Preço: {{ btc_context.last_price | round(2) }}</span>
                <span class="pill">4H: {{ btc_context.trend_4h }}</span>
                <span class="pill">5M: {{ btc_context.trend_5m }}</span>
                <span class="pill">Pressão: {{ btc_context.pressure }}</span>
                <span class="pill">Variação curta: {{ btc_context.short_change_percent }}%</span>

                <p>{{ btc_context.risk_message }}</p>
            </div>

            <div class="card col-12">
                <h2>Top Oportunidades do Ciclo</h2>

                {% if top_opportunities %}
                    <table>
                        <thead>
                            <tr>
                                <th>Ativo</th>
                                <th>Direção</th>
                                <th>Score</th>
                                <th>Classificação</th>
                                <th>Preço</th>
                                <th>Volume 24h</th>
                                <th>Risco</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in top_opportunities %}
                            <tr>
                                <td><strong>{{ item.symbol }}</strong></td>
                                <td>{{ item.direction }}</td>
                                <td><span class="score">{{ item.score }}</span></td>
                                <td>{{ item.classification }}</td>
                                <td>{{ "%.6f"|format(item.last_price) }}</td>
                                <td>{{ "{:,.0f}".format(item.quote_volume) }}</td>
                                <td>{{ item.risk_engine.risk_level }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% else %}
                    <p>Nenhuma oportunidade encontrada neste ciclo.</p>
                {% endif %}
            </div>

            <div class="card col-12">
                <h2>Análise dos Ativos</h2>

                {% for item in assets_analysis %}
                    <div class="card" style="margin-bottom: 16px; background: #0f172a;">
                        <h3>{{ item.symbol }}</h3>

                        {% if item.status != "OK" %}
                            <p>{{ item.message }}</p>
                        {% else %}
                            <span class="pill pill-blue">Preço: {{ "%.6f"|format(item.last_price) }}</span>
                            <span class="pill">Variação 24h: {{ item.price_change_percent }}%</span>
                            <span class="pill">Direção: {{ item.direction }}</span>
                            <span class="pill">Score: {{ item.score }}</span>
                            <span class="pill">Classificação: {{ item.classification }}</span>

                            <p></p>

                            <div class="grid">
                                <div class="card col-6" style="background:#111827;">
                                    <h3>4H</h3>
                                    <p><strong>Tendência:</strong> {{ item.analysis_4h.trend.trend }}</p>
                                    <p class="muted">{{ item.analysis_4h.trend.description }}</p>
                                    <p><strong>Suporte:</strong> {{ "%.6f"|format(item.analysis_4h.levels.support) }}</p>
                                    <p><strong>Resistência:</strong> {{ "%.6f"|format(item.analysis_4h.levels.resistance) }}</p>
                                    <p><strong>Distância suporte:</strong> {{ item.analysis_4h.distance.distance_to_support_percent }}%</p>
                                    <p><strong>Distância resistência:</strong> {{ item.analysis_4h.distance.distance_to_resistance_percent }}%</p>
                                </div>

                                <div class="card col-6" style="background:#111827;">
                                    <h3>5M</h3>
                                    <p><strong>Tendência:</strong> {{ item.analysis_5m.trend.trend }}</p>
                                    <p class="muted">{{ item.analysis_5m.trend.description }}</p>
                                    <p><strong>Volume:</strong> {{ item.analysis_5m.volume.status }} — {{ item.analysis_5m.volume.volume_ratio }}x</p>
                                    <p><strong>Candles:</strong> {{ item.analysis_5m.candles.status }}</p>
                                    <p><strong>Rejeição:</strong> {{ item.analysis_5m.candles.rejection }}</p>
                                    <p><strong>Suporte:</strong> {{ "%.6f"|format(item.analysis_5m.levels.support) }}</p>
                                    <p><strong>Resistência:</strong> {{ "%.6f"|format(item.analysis_5m.levels.resistance) }}</p>
                                </div>
                            </div>

                            <p><strong>Pontos Long:</strong> {{ item.long_points }} | <strong>Pontos Short:</strong> {{ item.short_points }}</p>

                            {% if item.reasons %}
                                <p><strong>Leituras técnicas:</strong></p>
                                {% for reason in item.reasons %}
                                    <span class="pill pill-blue">{{ reason }}</span>
                                {% endfor %}
                            {% endif %}

                            {% if item.blocks %}
                                <p><strong>Bloqueios:</strong></p>
                                {% for block in item.blocks %}
                                    <span class="pill pill-red">{{ block }}</span>
                                {% endfor %}
                            {% endif %}

                            {% if item.alerts %}
                                <p><strong>Alertas:</strong></p>
                                {% for alert in item.alerts %}
                                    <span class="pill pill-yellow">{{ alert }}</span>
                                {% endfor %}
                            {% endif %}

                            <div class="info" style="margin-top: 12px;">
                                <strong>Motor de Risco Educacional:</strong>
                                {{ item.risk_engine.decision }} —
                                {{ item.risk_engine.risk_level }} —
                                {{ item.risk_engine.message }}
                            </div>

                            <div class="success" style="margin-top: 12px;">
                                <strong>3X Educacional:</strong>
                                {{ item.educational_3x.status }} —
                                {{ item.educational_3x.message }}
                                <br>
                                <strong>Reduce Only:</strong> {{ item.educational_3x.reduce_only }}
                            </div>
                        {% endif %}
                    </div>
                {% endfor %}
            </div>

            <div class="card col-12">
                <h2>Motor de Risco Educacional</h2>
                <p>O motor avalia apenas critérios educacionais: direção, score, BTC, volume, candles, suporte, resistência e bloqueios técnicos.</p>
                <div class="warning">
                    Este robô não recomenda investimento, não executa ordens e não substitui autorização humana.
                </div>
            </div>

            <div class="card col-12">
                <h2>3X Educacional</h2>
                <p>
                    O bloco de 3X é apenas uma simulação conceitual. Qualquer saída parcial deve ser tratada como
                    <strong>Reduce Only</strong> para evitar aumento acidental de posição.
                </p>
                <div class="warning">
                    Nada neste painel deve ser interpretado como ordem de compra, venda, alavancagem ou recomendação financeira.
                </div>
            </div>

        </div>
    </div>
</body>
</html>
"""


# ============================================================
# Rotas
# ============================================================


@app.route("/")
def home():
    return """
    <html>
        <head>
            <title>ÁGUIA MASTER BOT</title>
            <meta charset="UTF-8">
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
            <p><a href="/api/report">Ver JSON do Ciclo</a></p>
        </body>
    </html>
    """


@app.route("/dashboard")
def dashboard():
    report = build_cycle_report()

    summary = report.get("summary", {})
    general_decision = report.get("general_decision", {})
    btc_context = report.get("btc_context", {})
    top_opportunities = report.get("top_opportunities", [])
    assets_analysis = report.get("assets_analysis", [])

    return render_template_string(
        DASHBOARD_HTML,
        summary=summary,
        general_decision=general_decision,
        btc_context=btc_context,
        top_opportunities=top_opportunities,
        assets_analysis=assets_analysis,
    )


@app.route("/api/report")
def api_report():
    report = build_cycle_report()
    return jsonify(report)


@app.route("/health")
def health():
    return jsonify(
        {
            "status": "ok",
            "app": APP_NAME,
            "mode": APP_MODE,
            "version": VERSION,
            "orders_enabled": False,
            "timestamp": now_utc_text(),
        }
    )


# ============================================================
# Execução local
# ============================================================


if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)