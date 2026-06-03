import os
import time
from datetime import datetime, timezone

import requests
from flask import Flask, jsonify, render_template_string

from exchange_binance import get_binance_testnet_diagnostic


app = Flask(__name__)


APP_NAME = "ÁGUIA MASTER BOT"
APP_MODE = "OBSERVADOR EDUCACIONAL"
APP_VERSION = "1.1.2"

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
            "ok": False,
            "error": "Não foi possível carregar candles.",
        }

    trend_4h = analyze_trend(candles_4h)
    trend_5m = analyze_trend(candles_5m)
    levels_5m = analyze_levels(candles_5m)
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

    phase = classify_setup_phase(
        score_data,
        direction_data,
        levels_5m,
        volume,
        candles,
    )

    risk = build_risk_engine(score_data, direction_data, btc_context)
    educational_3x = build_educational_3x(score_data, direction_data)

    return {
        "symbol": symbol,
        "ok": True,
        "price": ticker["last_price"],
        "quote_volume": ticker["quote_volume"],
        "change_percent": ticker["change_percent"],
        "trend_4h": trend_4h,
        "trend_5m": trend_5m,
        "levels_5m": levels_5m,
        "volume": volume,
        "candles": candles,
        "direction": direction_data,
        "score": score_data,
        "phase": phase,
        "risk": risk,
        "educational_3x": educational_3x,
    }


def build_cycle_report():
    started = time.time()

    btc_context = analyze_btc_context()
    tickers = get_24h_tickers()

    analyses = []

    for ticker in tickers:
        analyses.append(analyze_asset(ticker, btc_context))

    valid = [a for a in analyses if a.get("ok")]

    possible_longs = [
        a for a in valid if a["direction"]["direction"] == "POSSÍVEL LONG"
    ]

    possible_shorts = [
        a for a in valid if a["direction"]["direction"] == "POSSÍVEL SHORT"
    ]

    setups_in_formation = [
        a for a in valid if a["phase"]["phase"] == "SETUP EM FORMAÇÃO"
    ]

    top_opportunities = sorted(
        valid,
        key=lambda x: x["score"]["score"],
        reverse=True,
    )[:5]

    strong_setups = [
        a for a in valid if a["score"]["score"] >= 70 and not a["score"]["hard_blocks"]
    ]

    if strong_setups:
        decision = {
            "status": "OBSERVAR SETUP",
            "color": "yellow",
            "reason": "Existem ativos com possível estrutura educacional, mas ainda exige confirmação humana.",
            "action": "Monitorar volume, candle de confirmação e posição no canal.",
        }
    else:
        decision = {
            "status": "NÃO OPERAR",
            "color": "red",
            "reason": "Nenhuma oportunidade operacional forte encontrada neste ciclo.",
            "action": "Preservar capital. Não operar no meio do canal, sem direção ou sem volume.",
        }

    duration = safe_round(time.time() - started, 2)

    return {
        "app": APP_NAME,
        "mode": APP_MODE,
        "version": APP_VERSION,
        "updated_at": now_utc(),
        "selection_mode": "AUTO_VOLUME_WITH_WHITE_LIST",
        "white_list": True,
        "duration": duration,
        "btc_context": btc_context,
        "assets_analyzed": len(valid),
        "possible_longs": possible_longs,
        "possible_shorts": possible_shorts,
        "setups_in_formation": setups_in_formation,
        "top_opportunities": top_opportunities,
        "analyses": valid,
        "decision": decision,
        "safety": {
            "orders_enabled": False,
            "real_orders_enabled": False,
            "testnet_orders_enabled": False,
            "message": "Este painel é apenas educacional. Nenhuma ordem automática é executada.",
        },
    }


def build_safe_order_plan():
    """
    Plano fixo e seguro apenas para visualização.
    Não envia ordem para Binance.
    Não executa compra ou venda.
    Serve somente para validar estrutura visual e lógica de segurança.
    """

    entry_price = 3000.0
    margin_usdt = 25.0
    leverage = 20
    notional_usdt = margin_usdt * leverage

    quantity = safe_round(notional_usdt / entry_price, 3)

    return {
        "ok": True,
        "route": "/api/order-plan",
        "action": "PREPARE_ONLY",
        "execution_status": "NÃO EXECUTADO",
        "environment": "BINANCE_FUTURES_TESTNET",
        "symbol": "ETHUSDT",
        "side": "BUY",
        "order_type": "LIMIT",
        "entry_price": entry_price,
        "margin_usdt": margin_usdt,
        "leverage": leverage,
        "notional_usdt": notional_usdt,
        "quantity": quantity,
        "partial_take_profit_price": 3060,
        "partial_close_percent": 50,
        "invalidation_price": 2900,
        "reduce_only_for_entry": False,
        "reduce_only_for_partial_exit": True,
        "human_confirmation_required": True,
        "trading_enabled": False,
        "testnet_orders_enabled": False,
        "safety_status": "BLOQUEADO PARA EXECUÇÃO",
        "safety_note": "Plano gerado em modo seguro. Nenhuma ordem foi enviada para a Binance.",
        "message": "Plano preparado em modo seguro. Nenhuma ordem deve ser executada automaticamente. Exige confirmação humana e validação final antes de qualquer teste.",
        "warnings": [],
        }


@app.route("/api/human-confirm")
def api_human_confirm():
    """
    Confirmação humana simulada e segura.

    Esta rota NÃO executa ordem.
    Ela apenas registra que o usuário confirmou manualmente o plano,
    mantendo a execução bloqueada até uma futura validação do motor de risco.
    """
    return jsonify({
        "ok": True,
        "route": "/api/human-confirm",
        "action": "HUMAN_CONFIRMATION_RECEIVED",
        "execution_status": "NÃO EXECUTADO",
        "human_confirmation": True,
        "risk_engine_required": True,
        "trading_enabled": False,
        "testnet_orders_enabled": False,
        "real_orders_enabled": False,
        "safety_status": "BLOQUEADO PARA EXECUÇÃO",
        "message": "Confirmação humana recebida. Ordem ainda bloqueada. Próxima etapa: validação final do motor de risco.",
        "safety_note": "Esta confirmação não envia ordem para a Binance. Ela apenas registra a aprovação manual do plano.",
        "next_step": "VALIDAÇÃO_FINAL_DO_MOTOR_DE_RISCO"
    })


def css_badge_class(color):
    if color == "green":
        return "badge-green"
    if color == "yellow":
        return "badge-yellow"
    if color == "red":
        return "badge-red"
    return "badge-gray"


def safe_text(value, default="-"):
    if value is None:
        return default
    return str(value)


HTML_TEMPLATE = """
<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <title>{{ report.app }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <style>
        :root {
            --bg: #070d1c;
            --panel: #1c293d;
            --panel-2: #0e1729;
            --text: #f8fafc;
            --muted: #9fb3c8;
            --line: #334155;
            --blue: #2563eb;
            --green: #22c55e;
            --yellow: #f59e0b;
            --red: #ef4444;
            --gray: #64748b;
        }

        * {
            box-sizing: border-box;
        }

        body {
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family: Arial, Helvetica, sans-serif;
            font-size: 15px;
        }

        .container {
            width: min(980px, calc(100% - 28px));
            margin: 40px auto;
        }

        h1 {
            font-size: 34px;
            margin: 0 0 8px 0;
        }

        h2 {
            margin: 0 0 16px 0;
            font-size: 22px;
        }

        h3 {
            margin: 0 0 10px 0;
            font-size: 17px;
        }

        p {
            line-height: 1.5;
        }

        .subtitle {
            color: var(--muted);
            margin-bottom: 8px;
        }

        .updated {
            color: var(--muted);
            margin-bottom: 22px;
            font-size: 13px;
        }

        .card {
            background: var(--panel);
            border-radius: 14px;
            padding: 22px;
            margin: 18px 0;
            border: 1px solid rgba(255, 255, 255, 0.04);
        }

        .card-red {
            border-left: 5px solid var(--red);
        }

        .card-yellow {
            border-left: 5px solid var(--yellow);
        }

        .card-green {
            border-left: 5px solid var(--green);
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 12px;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 12px;
        }

        .box {
            background: var(--panel-2);
            border-radius: 9px;
            padding: 12px;
            min-height: 58px;
        }

        .box strong {
            display: block;
            font-size: 13px;
            color: #ffffff;
            margin-bottom: 4px;
        }

        .box span {
            color: #ffffff;
        }

        .muted {
            color: var(--muted);
        }

        .small {
            font-size: 12px;
        }

        .badge {
            display: inline-block;
            padding: 6px 10px;
            border-radius: 999px;
            font-weight: 700;
            font-size: 12px;
            color: #fff;
            margin: 4px 6px 4px 0;
        }

        .badge-green {
            background: var(--green);
        }

        .badge-yellow {
            background: var(--yellow);
        }

        .badge-red {
            background: var(--red);
        }

        .badge-gray {
            background: var(--gray);
        }

        .badge-blue {
            background: var(--blue);
        }

        .asset {
            border-left: 4px solid var(--line);
            background: rgba(15, 23, 42, 0.55);
            border-radius: 12px;
            padding: 16px;
            margin: 14px 0;
        }

        .asset.green {
            border-left-color: var(--green);
        }

        .asset.yellow {
            border-left-color: var(--yellow);
        }

        .asset.red {
            border-left-color: var(--red);
        }

        .asset.gray {
            border-left-color: var(--gray);
        }

        .alert {
            border: 1px solid rgba(239, 68, 68, 0.8);
            background: rgba(239, 68, 68, 0.13);
            color: #fecaca;
            padding: 10px 12px;
            border-radius: 8px;
            margin: 12px 0;
        }

        .note {
            border: 1px solid rgba(37, 99, 235, 0.8);
            background: rgba(37, 99, 235, 0.13);
            color: #bfdbfe;
            padding: 10px 12px;
            border-radius: 8px;
            margin: 12px 0;
        }

        ul {
            padding-left: 20px;
        }

        li {
            margin: 4px 0;
        }

        a {
            color: #93c5fd;
        }

        .footer {
            margin-top: 20px;
            color: var(--muted);
            font-size: 12px;
        }

        @media (max-width: 760px) {
            .grid,
            .grid-2 {
                grid-template-columns: 1fr;
            }

            .container {
                margin: 18px auto;
            }

            h1 {
                font-size: 28px;
            }
        }
    </style>
</head>

<body>
<div class="container">

    <h1>🦅 {{ report.app }}</h1>
    <p class="subtitle">Robô observador do Método Águia Cripto — modo seguro, educacional e sem execução de ordens.</p>
    <p class="updated">Última atualização: {{ report.updated_at }}</p>

    <div class="card">
        <h2>Resumo do Ciclo</h2>

        <div class="grid">
            <div class="box">
                <strong>Modo seleção:</strong>
                <span>{{ report.selection_mode }}</span>
            </div>

            <div class="box">
                <strong>Lista branca:</strong>
                <span>{{ report.white_list }}</span>
            </div>

            <div class="box">
                <strong>Ativos analisados:</strong>
                <span>{{ report.assets_analyzed }}</span>
            </div>

            <div class="box">
                <strong>Duração:</strong>
                <span>{{ report.duration }}s</span>
            </div>

            <div class="box">
                <strong>Possíveis Longs:</strong>
                <span>{{ report.possible_longs|length }}</span>
            </div>

            <div class="box">
                <strong>Possíveis Shorts:</strong>
                <span>{{ report.possible_shorts|length }}</span>
            </div>

            <div class="box">
                <strong>Aguardando:</strong>
                <span>{{ report.setups_in_formation|length }}</span>
            </div>

            <div class="box">
                <strong>Versão:</strong>
                <span>{{ report.version }}</span>
            </div>
        </div>
    </div>

    <div class="card card-{{ report.decision.color }}">
        <h2>Decisão Geral do Ciclo</h2>

        <span class="badge badge-{{ report.decision.color }}">{{ report.decision.status }}</span>

        <p><strong>Motivo:</strong> {{ report.decision.reason }}</p>
        <p><strong>Ação recomendada:</strong> {{ report.decision.action }}</p>

        <p class="muted small">
            Regra de segurança: este robô está em modo observador. Nenhuma ordem real ou testnet é executada automaticamente.
        </p>
    </div>

    <div class="card">
        <h2>Contexto BTC</h2>

        <div class="grid">
            <div class="box">
                <strong>Preço:</strong>
                <span>{{ format_price(report.btc_context.price) }}</span>
            </div>

            <div class="box">
                <strong>4H:</strong>
                <span>{{ report.btc_context.trend_4h }}</span>
            </div>

            <div class="box">
                <strong>5M:</strong>
                <span>{{ report.btc_context.trend_5m }}</span>
            </div>

            <div class="box">
                <strong>Pressão:</strong>
                <span>{{ report.btc_context.pressure }}</span>
            </div>

            <div class="box">
                <strong>Variação curta:</strong>
                <span>{{ report.btc_context.short_change_percent }}%</span>
            </div>
        </div>

        <p>{{ report.btc_context.message }}</p>
    </div>

    <div class="card {{ 'card-green' if binance.connected else 'card-red' }}">
        <h2>Binance Futures Testnet</h2>

        {% if binance.connected %}
            <span class="badge badge-green">CONECTADO</span>
        {% else %}
            <span class="badge badge-red">NÃO CONECTADO</span>
        {% endif %}

        <span class="badge badge-blue">CORRETORA API: BINANCE FUTURES</span>
        <span class="badge badge-red">EXECUÇÃO AUTOMÁTICA BLOQUEADA</span>

        <div class="grid">
            <div class="box">
                <strong>Ambiente:</strong>
                <span>{{ binance.environment }}</span>
            </div>

            <div class="box">
                <strong>API Key:</strong>
                <span>{{ "Detectada" if binance.has_api_key else "Ausente" }}</span>
            </div>

            <div class="box">
                <strong>Secret Key:</strong>
                <span>{{ "Detectada" if binance.has_api_secret else "Ausente" }}</span>
            </div>

            <div class="box">
                <strong>Testnet:</strong>
                <span>{{ binance.use_testnet }}</span>
            </div>

            <div class="box">
                <strong>Trading:</strong>
                <span>{{ binance.trading_enabled }}</span>
            </div>

            <div class="box">
                <strong>Human Confirm:</strong>
                <span>{{ binance.human_confirm_required }}</span>
            </div>

            <div class="box">
                <strong>Segurança:</strong>
                <span>{{ binance.safety_status }}</span>
            </div>

            <div class="box">
                <strong>Ordens:</strong>
                <span>{{ "Liberadas" if binance.orders_enabled_now else "Bloqueadas" }}</span>
            </div>
        </div>

        <p><strong>Mensagem:</strong> {{ binance.message }}</p>

        <div class="note">
            <strong>Saldo USDT Testnet:</strong><br>
            Saldo: {{ binance.balance.balance if binance.balance else 0 }} |
            Disponível: {{ binance.balance.availableBalance if binance.balance else 0 }} |
            Carteira: {{ binance.balance.crossWalletBalance if binance.balance else 0 }}
        </div>

        <div class="note">
            <strong>Posições abertas:</strong>
            {{ binance.positions.count if binance.positions else 0 }}
        </div>

        <div class="note">
            <strong>Ordens abertas:</strong>
            {{ binance.open_orders.count if binance.open_orders else 0 }}
        </div>

        {% if not binance.connected %}
            <div class="alert">
                Atenção: a Binance Futures Testnet está configurada, mas o servidor atual pode estar bloqueado pela Binance por restrição de localização.
                Mesmo assim, as chaves foram detectadas e a execução automática continua bloqueada.
            </div>
        {% endif %}
    </div>

    <div class="card">
        <h2>Radar de Setup em Formação</h2>
        <p class="muted small">
            Este bloco mostra ativos que ainda não são operação, mas que merecem observação.
        </p>

        {% if report.setups_in_formation %}
            {% for asset in report.setups_in_formation %}
                <div class="asset {{ asset.phase.color }}">
                    <h3>{{ asset.symbol }}</h3>

                    <span class="badge badge-blue">Score: {{ asset.score.score }}</span>
                    <span class="badge badge-gray">Direção: {{ asset.direction.direction }}</span>
                    <span class="badge badge-gray">Canal 5M: {{ asset.levels_5m.channel_position }}</span>
                    <span class="badge badge-gray">Volume: {{ asset.volume.status }}</span>
                    <span class="badge badge-{{ asset.phase.color }}">{{ asset.phase.phase }}</span>

                    <p><strong>Ação:</strong> {{ asset.phase.action }}</p>

                    {% if asset.score.warnings %}
                        <p><strong>Alertas:</strong></p>
                        <ul>
                            {% for warning in asset.score.warnings %}
                                <li>⚠️ {{ warning }}</li>
                            {% endfor %}
                        </ul>
                    {% endif %}
                </div>
            {% endfor %}
        {% else %}
            <div class="note">Nenhum setup em formação encontrado neste ciclo.</div>
        {% endif %}
    </div>

    <div class="card">
        <h2>Top Oportunidades do Ciclo</h2>

        {% if report.top_opportunities %}
            {% for asset in report.top_opportunities %}
                <div class="asset {{ asset.phase.color }}">
                    <h3>#{{ loop.index }} {{ asset.symbol }}</h3>

                    <span class="badge badge-blue">Score: {{ asset.score.score }}</span>
                    <span class="badge badge-gray">Preço: {{ format_price(asset.price) }}</span>
                    <span class="badge badge-gray">Direção: {{ asset.direction.direction }}</span>
                    <span class="badge badge-gray">Confiança: {{ asset.score.label }}</span>
                    <span class="badge badge-gray">Volume 24h: {{ format_money(asset.quote_volume) }}</span>
                    <span class="badge badge-{{ asset.phase.color }}">{{ asset.phase.phase }}</span>

                    <p><strong>Leitura:</strong> {{ asset.phase.action }}</p>

                    {% if asset.score.hard_blocks %}
                        <p><strong>Pontos de atenção:</strong></p>
                        <ul>
                            {% for block in asset.score.hard_blocks %}
                                <li>🔴 {{ block }}</li>
                            {% endfor %}
                        </ul>
                    {% endif %}

                    {% if asset.score.warnings %}
                        <p><strong>Travamentos de segurança:</strong></p>
                        <ul>
                            {% for warning in asset.score.warnings %}
                                <li>⚠️ {{ warning }}</li>
                            {% endfor %}
                        </ul>
                    {% endif %}
                </div>
            {% endfor %}
        {% else %}
            <div class="note">Nenhuma oportunidade encontrada neste ciclo.</div>
        {% endif %}
    </div>

    <div class="card">
        <h2>Análise dos Ativos</h2>

        {% if report.analyses %}
            {% for asset in report.analyses %}
                <div class="asset {{ asset.phase.color }}">
                    <h3>{{ asset.symbol }}</h3>

                    <span class="badge badge-blue">Preço: {{ format_price(asset.price) }}</span>
                    <span class="badge badge-gray">Score: {{ asset.score.score }}</span>
                    <span class="badge badge-gray">Direção: {{ asset.direction.direction }}</span>
                    <span class="badge badge-gray">4H: {{ asset.trend_4h.status }}</span>
                    <span class="badge badge-gray">5M: {{ asset.trend_5m.status }}</span>
                    <span class="badge badge-gray">Volume: {{ asset.volume.status }}</span>
                    <span class="badge badge-gray">Canal 5M: {{ asset.levels_5m.channel_position }}</span>
                    <span class="badge badge-{{ asset.phase.color }}">{{ asset.phase.phase }}</span>

                    <div class="grid-2">
                        <div class="box">
                            <strong>4H — Contexto</strong>
                            <p>Tendência: {{ asset.trend_4h.status }}</p>
                            <p>{{ asset.trend_4h.description }}</p>
                            <p>Suporte: {{ format_price(asset.levels_5m.support) }}</p>
                            <p>Resistência: {{ format_price(asset.levels_5m.resistance) }}</p>
                        </div>

                        <div class="box">
                            <strong>5M — Gatilho</strong>
                            <p>Tendência: {{ asset.trend_5m.status }}</p>
                            <p>Candles: {{ asset.candles.status }}</p>
                            <p>Rejeição: {{ asset.candles.rejection }}</p>
                            <p>Volume: {{ asset.volume.status }} — {{ asset.volume.ratio }}x</p>
                        </div>
                    </div>

                    <p><strong>Motivos positivos:</strong></p>
                    {% if asset.direction.reasons %}
                        <ul>
                            {% for reason in asset.direction.reasons %}
                                <li>✅ {{ reason }}</li>
                            {% endfor %}
                        </ul>
                    {% else %}
                        <p class="muted">Nenhum motivo forte encontrado.</p>
                    {% endif %}

                    <p><strong>Diagnóstico:</strong></p>
                    {% if asset.direction.blocks %}
                        <ul>
                            {% for block in asset.direction.blocks %}
                                <li>🔴 {{ block }}</li>
                            {% endfor %}
                        </ul>
                    {% else %}
                        <p class="muted">Sem bloqueios técnicos relevantes.</p>
                    {% endif %}

                    <div class="note">
                        <strong>Motor de Risco Educacional:</strong>
                        {{ asset.risk.status }} — {{ asset.risk.message }}
                    </div>

                    <div class="alert">
                        <strong>3X Educacional:</strong>
                        {{ asset.educational_3x.status }} — {{ asset.educational_3x.message }}<br>
                        Redução Only: {{ asset.educational_3x.reduce_only }}
                    </div>
                </div>
            {% endfor %}
        {% else %}
            <div class="note">Nenhum ativo analisado neste ciclo.</div>
        {% endif %}
    </div>

    <div class="card">
        <h2>Proposta Segura da Ordem</h2>
        <p class="muted small">
            Esta proposta é apenas um plano seguro. Nenhuma ordem é executada automaticamente.
        </p>

        <div class="grid">
            <div class="box">
                <strong>Ação:</strong>
                <span id="op-action">Carregando...</span>
            </div>

            <div class="box">
                <strong>Execução:</strong>
                <span id="op-execution">Carregando...</span>
            </div>

            <div class="box">
                <strong>Segurança:</strong>
                <span id="op-safety">Carregando...</span>
            </div>

            <div class="box">
                <strong>Confirmação humana:</strong>
                <span id="op-human">Carregando...</span>
            </div>

            <div class="box">
                <strong>Ativo:</strong>
                <span id="op-symbol">Carregando...</span>
            </div>

            <div class="box">
                <strong>Direção:</strong>
                <span id="op-side">Carregando...</span>
            </div>

            <div class="box">
                <strong>Tipo:</strong>
                <span id="op-type">Carregando...</span>
            </div>

            <div class="box">
                <strong>Entrada:</strong>
                <span id="op-entry">Carregando...</span>
            </div>

            <div class="box">
                <strong>Margem:</strong>
                <span id="op-margin">Carregando...</span>
            </div>

            <div class="box">
                <strong>Alavancagem:</strong>
                <span id="op-leverage">Carregando...</span>
            </div>

            <div class="box">
                <strong>Valor nocional:</strong>
                <span id="op-notional">Carregando...</span>
            </div>

            <div class="box">
                <strong>Quantidade:</strong>
                <span id="op-quantity">Carregando...</span>
            </div>

            <div class="box">
                <strong>Alvo parcial:</strong>
                <span id="op-take-profit">Carregando...</span>
            </div>

            <div class="box">
                <strong>Saída parcial:</strong>
                <span id="op-partial-close">Carregando...</span>
            </div>

            <div class="box">
                <strong>Invalidação:</strong>
                <span id="op-invalidation">Carregando...</span>
            </div>

            <div class="box">
                <strong>Reduce Only parcial:</strong>
                <span id="op-reduce-only">Carregando...</span>
            </div>
        </div>

        <div class="note" id="op-message">
            Carregando proposta segura da ordem...
        </div>
    </div>

    <div class="card">
        <h2>Segurança Operacional</h2>

        <p>
            Este painel é apenas educacional. Ele não envia ordem automática, não executa compra ou venda
            e mantém qualquer operação bloqueada enquanto a confirmação humana não for implementada.
        </p>

        <div class="alert">
            Regra central: preservar capital vem antes de qualquer oportunidade.
        </div>
    </div>

    <p class="footer">
        Links rápidos:
        <a href="/api/report">API JSON</a> |
        <a href="/api/binance-testnet">Binance Testnet</a> |
        <a href="/api/order-plan">Plano de Ordem</a> |
        <a href="/health">Health</a> |
        <a href="/dashboard">Dashboard</a>
    </p>

</div>

<script>
    function setText(id, value) {
        var element = document.getElementById(id);

        if (!element) {
            return;
        }

        if (value === undefined || value === null || value === "") {
            element.textContent = "-";
            return;
        }

        element.textContent = value;
    }

    function loadOrderPlan() {
        fetch("/api/order-plan")
            .then(function (response) {
                return response.json();
            })
            .then(function (plan) {
                setText("op-action", plan.action || "-");
                setText("op-execution", plan.execution_status || "NÃO EXECUTADO");
                setText("op-safety", plan.safety_status || "BLOQUEADO PARA EXECUÇÃO");
                setText("op-human", plan.human_confirmation_required ? "Obrigatória" : "Não");
                setText("op-symbol", plan.symbol || "-");
                setText("op-side", plan.side || "-");
                setText("op-type", plan.order_type || "-");
                setText("op-entry", plan.entry_price || "-");
                setText("op-margin", String(plan.margin_usdt || "-") + " USDT");
                setText("op-leverage", String(plan.leverage || "-") + "x");
                setText("op-notional", String(plan.notional_usdt || "-") + " USDT");
                setText("op-quantity", plan.quantity || "-");
                setText("op-take-profit", plan.partial_take_profit_price || "-");
                setText("op-partial-close", String(plan.partial_close_percent || "-") + "%");
                setText("op-invalidation", plan.invalidation_price || "-");
                setText("op-reduce-only", plan.reduce_only_for_partial_exit ? "Sim" : "Não");
                setText("op-message", plan.safety_note || plan.message || "Plano seguro carregado.");
            })
            .catch(function (error) {
                setText("op-action", "ERRO");
                setText("op-execution", "NÃO EXECUTADO");
                setText("op-safety", "BLOQUEADO PARA EXECUÇÃO");
                setText("op-message", "Não foi possível carregar a proposta segura de ordem: " + error);
            });
    }

    loadOrderPlan();
</script>

</body>
</html>
"""


@app.route("/")
def home():
    return dashboard()


@app.route("/dashboard")
def dashboard():
    report = build_cycle_report()

    try:
        binance = get_binance_testnet_diagnostic()
    except Exception as error:
        binance = {
            "connected": False,
            "environment": "BINANCE FUTURES DEMO/TESTNET",
            "has_api_key": False,
            "has_api_secret": False,
            "use_testnet": True,
            "trading_enabled": False,
            "human_confirm_required": True,
            "safety_status": "BLOQUEADO PARA EXECUÇÃO",
            "orders_enabled_now": False,
            "message": f"Erro ao carregar diagnóstico Binance: {error}",
            "balance": {
                "balance": 0,
                "availableBalance": 0,
                "crossWalletBalance": 0,
            },
            "positions": {
                "count": 0,
            },
            "open_orders": {
                "count": 0,
            },
        }

    return render_template_string(
        HTML_TEMPLATE,
        report=report,
        binance=binance,
        format_price=format_price,
        format_money=format_money,
        css_badge_class=css_badge_class,
    )


@app.route("/api/report")
def api_report():
    return jsonify(build_cycle_report())


@app.route("/api/binance-testnet")
def api_binance_testnet():
    try:
        diagnostic = get_binance_testnet_diagnostic()
        return jsonify(diagnostic)
    except Exception as error:
        return jsonify(
            {
                "ok": False,
                "connected": False,
                "error": str(error),
                "message": "Erro ao consultar diagnóstico da Binance Futures Testnet.",
                "safety_status": "BLOQUEADO PARA EXECUÇÃO",
                "trading_enabled": False,
                "testnet_orders_enabled": False,
            }
        )


@app.route("/api/order-plan")
def api_order_plan():
    return jsonify(build_safe_order_plan())


@app.route("/health")
def health():
    return jsonify(
        {
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