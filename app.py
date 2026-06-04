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
    binance_testnet = get_binance_testnet_diagnostic()
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
        "binance_testnet": binance_testnet,
        "top_opportunities": top_opportunities,
        "setup_radar": setup_radar,
        "assets": valid_assets,
    }


def build_safe_order_plan():
    """
    Proposta fixa e segura de ordem.
    Esta função NÃO executa ordem.
    Serve apenas para exibir no dashboard e validar o fluxo de segurança.
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
        "real_orders_enabled": False,
        "safety_status": "BLOQUEADO PARA EXECUÇÃO",
        "safety_note": "Plano gerado em modo seguro. Nenhuma ordem foi enviada para a Binance.",
        "message": "Plano preparado em modo seguro. Nenhuma ordem deve ser executada automaticamente. Exige confirmação humana e validação final antes de qualquer teste.",
        "warnings": [],
    }


def build_human_confirmation():
    """
    Confirmação humana simulada e segura.
    Esta função NÃO executa ordem.
    Ela apenas registra que o usuário confirmou manualmente o plano.
    """

    return {
        "ok": True,
        "route": "/api/human-confirm",
        "action": "HUMAN_CONFIRMATION_RECEIVED",
        "execution_status": "NÃO EXECUTADO",
        "human_confirmation": True,
        "risk_engine_required": True,
        "next_step": "VALIDAÇÃO_FINAL_DO_MOTOR_DE_RISCO",
        "trading_enabled": False,
        "testnet_orders_enabled": False,
        "real_orders_enabled": False,
        "safety_status": "BLOQUEADO PARA EXECUÇÃO",
        "safety_note": "Esta confirmação não envia ordem para a Binance. Ela apenas registra a aprovação manual do plano.",
        "message": "Confirmação humana recebida. Ordem ainda bloqueada. Próxima etapa: validação final do motor de risco.",
    }

def build_risk_final_validation():
    plan = build_safe_order_plan()

    warnings = []
    blocks = []
    decision = "APROVAR_TESTE"
    risk_level = "BAIXO"
    action_recommended = "Plano pode seguir para simulação segura, sem execução automática."

    margin_usdt = float(plan.get("margin_usdt", 0) or 0)
    leverage = int(plan.get("leverage", 0) or 0)
    entry_price = float(plan.get("entry_price", 0) or 0)
    invalidation_price = float(plan.get("invalidation_price", 0) or 0)
    notional_usdt = float(plan.get("notional_usdt", 0) or 0)

    trading_enabled = bool(plan.get("trading_enabled", False))
    testnet_orders_enabled = bool(plan.get("testnet_orders_enabled", False))
    real_orders_enabled = bool(plan.get("real_orders_enabled", False))
    human_confirmation_required = bool(plan.get("human_confirmation_required", True))

    if trading_enabled:
        blocks.append("TRADING_ENABLED não pode estar ativo nesta fase.")
        decision = "KILL_SWITCH"
        risk_level = "CRÍTICO"

    if testnet_orders_enabled:
        blocks.append("TESTNET_ORDERS_ENABLED não pode estar ativo nesta fase.")
        decision = "KILL_SWITCH"
        risk_level = "CRÍTICO"

    if real_orders_enabled:
        blocks.append("REAL_ORDERS_ENABLED não pode estar ativo nesta fase.")
        decision = "KILL_SWITCH"
        risk_level = "CRÍTICO"

    if not human_confirmation_required:
        blocks.append("Confirmação humana obrigatória não está ativa.")
        decision = "BLOQUEAR"
        risk_level = "ALTO"

    if margin_usdt <= 0:
        blocks.append("Margem inválida ou zerada.")
        decision = "BLOQUEAR"
        risk_level = "ALTO"

    if leverage <= 0:
        blocks.append("Alavancagem inválida ou zerada.")
        decision = "BLOQUEAR"
        risk_level = "ALTO"

    if leverage > 20:
        warnings.append("Alavancagem acima de 20x. Exige cautela elevada.")
        if decision == "APROVAR_TESTE":
            decision = "PAUSAR"
            risk_level = "MÉDIO/ALTO"

    if margin_usdt > 25:
        warnings.append("Margem acima do limite educacional inicial de 25 USDT.")
        if decision == "APROVAR_TESTE":
            decision = "PAUSAR"
            risk_level = "MÉDIO"

    if notional_usdt > 500:
        warnings.append("Valor nocional acima de 500 USDT.")
        if decision == "APROVAR_TESTE":
            decision = "PAUSAR"
            risk_level = "MÉDIO"

    if entry_price <= 0:
        blocks.append("Preço de entrada inválido.")
        decision = "BLOQUEAR"
        risk_level = "ALTO"

    if invalidation_price <= 0:
        blocks.append("Preço de invalidação inválido.")
        decision = "BLOQUEAR"
        risk_level = "ALTO"

    if entry_price > 0 and invalidation_price > 0:
        distance_percent = abs(entry_price - invalidation_price) / entry_price * 100

        if distance_percent > 5:
            warnings.append("Invalidação muito distante da entrada. Risco técnico elevado.")
            if decision == "APROVAR_TESTE":
                decision = "PAUSAR"
                risk_level = "MÉDIO/ALTO"
    else:
        distance_percent = 0

    if blocks:
        action_recommended = "Não seguir para teste. Corrigir bloqueios antes de qualquer simulação."

    if decision == "KILL_SWITCH":
        action_recommended = "Parar imediatamente. Alguma trava crítica foi violada."

    if decision == "PAUSAR":
        action_recommended = "Pausar e revisar parâmetros antes de seguir."

    return {
        "ok": len(blocks) == 0,
        "route": "/api/risk-final-validation",
        "action": "RISK_FINAL_VALIDATION",
        "decision": decision,
        "execution_status": "NÃO EXECUTADO",
        "risk_level": risk_level,
        "action_recommended": action_recommended,
        "symbol": plan.get("symbol"),
        "side": plan.get("side"),
        "order_type": plan.get("order_type"),
        "entry_price": entry_price,
        "invalidation_price": invalidation_price,
        "distance_to_invalidation_percent": round(distance_percent, 2),
        "margin_usdt": margin_usdt,
        "leverage": leverage,
        "notional_usdt": notional_usdt,
        "quantity": plan.get("quantity"),
        "partial_take_profit_price": plan.get("partial_take_profit_price"),
        "partial_close_percent": plan.get("partial_close_percent"),
        "reduce_only_for_partial_exit": plan.get("reduce_only_for_partial_exit"),
        "human_confirmation_required": human_confirmation_required,
        "trading_enabled": trading_enabled,
        "testnet_orders_enabled": testnet_orders_enabled,
        "real_orders_enabled": real_orders_enabled,
        "safety_status": "BLOQUEADO PARA EXECUÇÃO",
        "next_step": "AGUARDAR_APROVACAO_MANUAL_FINAL",
        "warnings": warnings,
        "blocks": blocks,
        "message": "Validação final do motor de risco concluída. Nenhuma ordem foi enviada para a Binance.",
        "safety_note": "Esta etapa apenas valida risco. Não executa ordem real nem testnet.",
    }

def build_testnet_simulation():
    """
    Simulação Testnet Controlada.
    Esta função NÃO envia ordem para a Binance.
    Ela apenas simula a próxima etapa após a validação final do motor de risco.
    """

    validation = build_risk_final_validation()

    simulation_steps = [
        "1. Ler proposta segura da ordem.",
        "2. Confirmar que houve validação humana.",
        "3. Confirmar validação final do motor de risco.",
        "4. Conferir se execução automática continua bloqueada.",
        "5. Preparar simulação didática da ordem.",
        "6. Manter envio real e testnet bloqueados até autorização futura.",
    ]

    simulated_order = {
        "symbol": validation.get("symbol", "ETHUSDT"),
        "side": validation.get("side", "BUY"),
        "order_type": validation.get("order_type", "LIMIT"),
        "entry_price": validation.get("entry_price"),
        "quantity": validation.get("quantity"),
        "margin_usdt": validation.get("margin_usdt"),
        "leverage": validation.get("leverage"),
        "notional_usdt": validation.get("notional_usdt"),
        "partial_take_profit_price": validation.get("partial_take_profit_price"),
        "partial_close_percent": validation.get("partial_close_percent"),
        "invalidation_price": validation.get("invalidation_price"),
        "reduce_only_for_entry": False,
        "reduce_only_for_partial_exit": True,
    }

    return {
        "ok": True,
        "route": "/api/testnet-simulation",
        "action": "TESTNET_SIMULATION_ONLY",
        "execution_status": "NÃO EXECUTADO",
        "simulation_status": "SIMULAÇÃO PREPARADA",
        "environment": "BINANCE_FUTURES_TESTNET_SIMULATED",
        "decision": validation.get("decision", "AGUARDAR"),
        "risk_level": validation.get("risk_level", "INDEFINIDO"),
        "human_confirmation_required": True,
        "risk_engine_required": True,
        "manual_final_approval_required": True,
        "trading_enabled": False,
        "testnet_orders_enabled": False,
        "real_orders_enabled": False,
        "safety_status": "BLOQUEADO PARA EXECUÇÃO",
        "next_step": "AGUARDAR_AUTORIZACAO_PARA_TESTE_CONTROLADO",
        "simulated_order": simulated_order,
        "simulation_steps": simulation_steps,
        "message": "Simulação testnet controlada preparada. Nenhuma ordem foi enviada para a Binance.",
        "safety_note": "Esta etapa é apenas uma simulação educacional. Não executa ordem real nem testnet.",
        "warnings": [
            "Execução automática continua bloqueada.",
            "Teste real na Testnet ainda depende de autorização humana futura.",
            "Nenhuma ordem foi enviada para a Binance nesta etapa.",
        ],
        "blocks": [
            "TRADING_ENABLED_FALSE",
            "TESTNET_ORDERS_ENABLED_FALSE",
            "REAL_ORDERS_ENABLED_FALSE",
        ],
    }

def build_manual_test_authorization():
    """
    Autorização manual para teste controlado.
    Esta função NÃO executa ordem.
    Ela apenas registra que o usuário autorizou seguir para uma etapa futura de teste controlado.
    Mesmo autorizada, a execução real e testnet continuam bloqueadas.
    """
    simulation = build_testnet_simulation()
    simulated_order = simulation.get("simulated_order", {})

    return {
        "ok": True,
        "route": "/api/manual-test-authorization",
        "action": "MANUAL_TEST_AUTHORIZATION_REGISTERED",
        "execution_status": "NÃO EXECUTADO",
        "authorization_status": "AUTORIZAÇÃO MANUAL REGISTRADA",
        "environment": "BINANCE_FUTURES_TESTNET_CONTROLLED",

        "symbol": simulated_order.get("symbol", "ETHUSDT"),
        "side": simulated_order.get("side", "BUY"),
        "order_type": simulated_order.get("order_type", "LIMIT"),
        "entry_price": simulated_order.get("entry_price"),
        "quantity": simulated_order.get("quantity"),
        "margin_usdt": simulated_order.get("margin_usdt"),
        "leverage": simulated_order.get("leverage"),
        "notional_usdt": simulated_order.get("notional_usdt"),
        "partial_take_profit_price": simulated_order.get("partial_take_profit_price"),
        "partial_close_percent": simulated_order.get("partial_close_percent"),
        "invalidation_price": simulated_order.get("invalidation_price"),

        "decision": "AUTORIZAR_PROXIMA_ETAPA_DIDATICA",
        "human_confirmation_required": True,
        "risk_engine_required": True,
        "manual_final_approval_required": True,
        "controlled_test_authorization": True,

        "trading_enabled": False,
        "testnet_orders_enabled": False,
        "real_orders_enabled": False,

        "safety_status": "BLOQUEADO PARA EXECUÇÃO",
        "next_step": "AGUARDAR_EXECUTOR_DIDATICO_TESTNET_CONTROLADO",

        "message": "Autorização manual registrada. Nenhuma ordem foi enviada para a Binance.",
        "safety_note": "Esta autorização não executa ordem real nem testnet. Ela apenas libera a próxima etapa didática controlada.",

        "warnings": [
            "Execução automática continua bloqueada.",
            "Ordens reais continuam desativadas.",
            "Ordens testnet continuam desativadas nesta etapa.",
            "A próxima etapa ainda dependerá de um executor didático separado.",
        ],
        "blocks": [
            "TRADING_ENABLED_FALSE",
            "TESTNET_ORDERS_ENABLED_FALSE",
            "REAL_ORDERS_ENABLED_FALSE",
            "MANUAL_AUTHORIZATION_ONLY",
        ],
    }

def build_mec_decision_engine():
    """
    Cérebro operacional inspirado na lógica do Método Águia Cripto.
    Objetivo: buscar oportunidades de ganho com leitura técnica, disciplina,
    proteção de banca e controle de risco.

    Esta função NÃO executa ordem.
    Ela apenas analisa o cenário e gera uma decisão operacional segura.
    """

    symbol = "ETHUSDT"

    market_context = {
        "symbol": symbol,
        "btc_trend": "LATERAL",
        "daily_trend": "LATERAL",
        "h4_context": "SUPORTE_COM_REJEICAO",
        "m5_context": "ROMPIMENTO_LOCAL_COM_VOLUME",
        "buyer_volume": "AUMENTANDO",
        "seller_volume": "CAINDO",
        "price_position": "PROXIMO_SUPORTE",
        "distance_to_resistance": "BOA",
        "entry_condition": "AGUARDAR_RETESTE",
    }

    risk_context = {
        "account_balance_usdt": 1000,
        "current_risk_percent": 4.5,
        "daily_loss_percent": 0,
        "weekly_loss_percent": 0,
        "open_positions": 3,
        "margin_usdt": 25,
        "leverage": 20,
        "entry_price": 3000,
        "invalidation_price": 2900,
        "partial_take_profit_price": 3060,
        "estimated_liquidation_price": 2850,
    }

    decision = "AGUARDAR_CONFIRMACAO"
    direction = "LONG"
    confidence = "MEDIA_ALTA"
    risk_status = "CONTROLADO"
    objective = "BUSCAR_GANHO_COM_RISCO_CONTROLADO"
    action_recommended = "MONITORAR_RETESTE_ANTES_DA_ENTRADA"
    entry_instruction = "Não entrar esticado. Aguardar pullback curto ou reteste da região rompida."
    protection_instruction = "Preservar capital vem antes de qualquer oportunidade."
    can_prepare_order_plan = False
    blocks = []
    warnings = []

    btc_trend = market_context["btc_trend"]
    daily_trend = market_context["daily_trend"]
    h4_context = market_context["h4_context"]
    m5_context = market_context["m5_context"]
    buyer_volume = market_context["buyer_volume"]
    seller_volume = market_context["seller_volume"]
    distance_to_resistance = market_context["distance_to_resistance"]

    current_risk = risk_context["current_risk_percent"]
    daily_loss = risk_context["daily_loss_percent"]
    weekly_loss = risk_context["weekly_loss_percent"]
    open_positions = risk_context["open_positions"]
    leverage = risk_context["leverage"]
    entry_price = risk_context["entry_price"]
    invalidation_price = risk_context["invalidation_price"]
    liquidation_price = risk_context["estimated_liquidation_price"]

    distance_to_invalidation_percent = round(
        abs(entry_price - invalidation_price) / entry_price * 100,
        2
    )

    distance_to_liquidation_percent = round(
        abs(entry_price - liquidation_price) / entry_price * 100,
        2
    )

    # Travas principais de segurança
    if daily_loss >= 5:
        decision = "KILL_SWITCH"
        direction = "NENHUMA"
        confidence = "BLOQUEADO"
        risk_status = "CRITICO"
        action_recommended = "PARAR_OPERACOES_NO_DIA"
        entry_instruction = "Não operar. Limite diário de perda atingido."
        can_prepare_order_plan = False
        blocks.append("DAILY_LOSS_LIMIT_REACHED")

    elif weekly_loss >= 12:
        decision = "BLOQUEAR"
        direction = "NENHUMA"
        confidence = "BLOQUEADO"
        risk_status = "ALTO"
        action_recommended = "PAUSAR_E_REAVALIAR_BANCA"
        entry_instruction = "Não operar. Risco semanal elevado."
        can_prepare_order_plan = False
        blocks.append("WEEKLY_LOSS_LIMIT_REACHED")

    elif current_risk >= 10:
        decision = "BLOQUEAR"
        direction = "NENHUMA"
        confidence = "BLOQUEADO"
        risk_status = "ALTO"
        action_recommended = "REDUZIR_RISCO_ANTES_DE_NOVA_ENTRADA"
        entry_instruction = "Não abrir nova operação com risco da banca elevado."
        can_prepare_order_plan = False
        blocks.append("ACCOUNT_RISK_TOO_HIGH")

    elif open_positions >= 5:
        decision = "BLOQUEAR"
        direction = "NENHUMA"
        confidence = "BLOQUEADO"
        risk_status = "ALTO"
        action_recommended = "EVITAR_EXCESSO_DE_OPERACOES_ABERTAS"
        entry_instruction = "Não abrir nova entrada. Muitas operações abertas."
        can_prepare_order_plan = False
        blocks.append("TOO_MANY_OPEN_POSITIONS")

    elif leverage > 20:
        decision = "BLOQUEAR"
        direction = "NENHUMA"
        confidence = "BLOQUEADO"
        risk_status = "ALTO"
        action_recommended = "REDUZIR_ALAVANCAGEM"
        entry_instruction = "Alavancagem acima do limite seguro desta fase."
        can_prepare_order_plan = False
        blocks.append("LEVERAGE_TOO_HIGH")

    # Lógica operacional para Long
    elif (
        btc_trend in ["LATERAL", "ALTA"]
        and daily_trend in ["LATERAL", "ALTA"]
        and h4_context == "SUPORTE_COM_REJEICAO"
        and m5_context == "ROMPIMENTO_LOCAL_COM_VOLUME"
        and buyer_volume == "AUMENTANDO"
        and seller_volume == "CAINDO"
        and distance_to_resistance == "BOA"
    ):
        decision = "OPERAR_COM_CAUTELA"
        direction = "LONG"
        confidence = "MEDIA_ALTA"
        risk_status = "CONTROLADO"
        action_recommended = "AGUARDAR_RETESTE_E_PREPARAR_PLANO"
        entry_instruction = "Existe oportunidade de Long, mas a entrada ideal é no reteste ou pullback curto."
        can_prepare_order_plan = True
        warnings.append("Evitar entrada esticada após candles fortes.")
        warnings.append("Confirmar se o BTC continua sem pressão contrária.")
        warnings.append("Usar invalidação técnica clara.")

    # Lógica para aguardar
    else:
        decision = "AGUARDAR"
        direction = "NENHUMA"
        confidence = "BAIXA"
        risk_status = "INDEFINIDO"
        action_recommended = "MONITORAR_MERCADO"
        entry_instruction = "Não existe confirmação suficiente para entrada agora."
        can_prepare_order_plan = False
        warnings.append("Sem confluência suficiente para operação.")

    forbidden_actions = [
        "Não operar por desespero.",
        "Não aumentar mão para recuperar prejuízo.",
        "Não entrar contra BTC forte.",
        "Não operar no meio do canal sem confirmação.",
        "Não usar alavancagem excessiva.",
        "Não ignorar invalidação técnica.",
    ]

    return {
        "ok": True,
        "route": "/api/mec-decision-engine",
        "action": "MEC_DECISION_ENGINE",
        "objective": objective,
        "symbol": symbol,
        "decision": decision,
        "direction": direction,
        "confidence": confidence,
        "risk_status": risk_status,
        "action_recommended": action_recommended,
        "entry_instruction": entry_instruction,
        "protection_instruction": protection_instruction,
        "can_prepare_order_plan": can_prepare_order_plan,
        "market_context": market_context,
        "risk_context": risk_context,
        "distance_to_invalidation_percent": distance_to_invalidation_percent,
        "distance_to_liquidation_percent": distance_to_liquidation_percent,
        "forbidden_actions": forbidden_actions,
        "warnings": warnings,
        "blocks": blocks,
        "trading_enabled": False,
        "testnet_orders_enabled": False,
        "real_orders_enabled": False,
        "safety_status": "ANALISE_OPERACIONAL_SEM_EXECUCAO",
        "next_step": "EXIBIR_DECISAO_MEC_NO_DASHBOARD",
        "message": "Cérebro MEC analisou o cenário. Nenhuma ordem foi enviada.",
    }

def build_controlled_testnet_executor():
    """
    Executor Didático Testnet Controlado.

    Esta função NÃO envia ordem para a Binance.
    Esta função NÃO executa compra ou venda.
    Esta função NÃO libera ordem real.
    Esta função apenas valida se o fluxo operacional está pronto
    para uma futura etapa didática de execução controlada em Testnet.
    """

    mec = build_mec_decision_engine()
    plan = build_safe_order_plan()
    human = build_human_confirmation()
    risk = build_risk_final_validation()
    simulation = build_testnet_simulation()
    manual_auth = build_manual_test_authorization()

    checks = {
    "mec_decision_loaded": bool(mec.get("ok")),
    "mec_allows_plan": bool(mec.get("can_prepare_order_plan")),
    "safe_order_plan_loaded": bool(plan.get("ok")),
    "human_confirmation_received": bool(human.get("human_confirmation")),
    "risk_engine_required": True,
    "risk_final_validation_loaded": bool(risk.get("ok")),
    "testnet_simulation_loaded": bool(simulation.get("ok")),
    "manual_authorization_registered": bool(manual_auth.get("ok")),
    "trading_disabled": not bool(plan.get("trading_enabled")),
    "testnet_orders_disabled": not bool(plan.get("testnet_orders_enabled")),
    "real_orders_disabled": not bool(plan.get("real_orders_enabled")),
   }

    blocks = []
    warnings = []

    decision = "EXECUTOR_DIDATICO_PREPARADO"
    executor_status = "BLOQUEADO_PARA_ENVIO_DE_ORDEM"
    execution_status = "NÃO EXECUTADO"
    next_step = "CRIAR_EXECUTOR_TESTNET_REAL_SOMENTE_COM_NOVA_AUTORIZACAO"
    action_recommended = "MANTER_EXECUTOR_EM_MODO_DIDATICO"

    if not checks["mec_decision_loaded"]:
        blocks.append("MEC_DECISION_NOT_LOADED")

    if not checks["mec_allows_plan"]:
        blocks.append("MEC_DOES_NOT_ALLOW_ORDER_PLAN")

    if not checks["safe_order_plan_loaded"]:
        blocks.append("SAFE_ORDER_PLAN_NOT_LOADED")

    if not checks["human_confirmation_received"]:
        blocks.append("HUMAN_CONFIRMATION_NOT_RECEIVED")

    if not checks["risk_final_validation_loaded"]:
        blocks.append("RISK_FINAL_VALIDATION_NOT_LOADED")

    if not checks["testnet_simulation_loaded"]:
        blocks.append("TESTNET_SIMULATION_NOT_LOADED")

    if not checks["manual_authorization_registered"]:
        blocks.append("MANUAL_AUTHORIZATION_NOT_REGISTERED")

    if not checks["trading_disabled"]:
        blocks.append("TRADING_ENABLED_SHOULD_BE_FALSE")

    if not checks["testnet_orders_disabled"]:
        blocks.append("TESTNET_ORDERS_ENABLED_SHOULD_BE_FALSE")

    if not checks["real_orders_disabled"]:
        blocks.append("REAL_ORDERS_ENABLED_SHOULD_BE_FALSE")

    if blocks:
        decision = "EXECUTOR_BLOQUEADO"
        executor_status = "BLOQUEADO_POR_SEGURANCA"
        action_recommended = "CORRIGIR_BLOQUEIOS_ANTES_DE_AVANCAR"
        next_step = "REVISAR_FLUXO_DE_SEGURANCA"
        warnings.append("Existem bloqueios no fluxo. Nenhuma etapa de execução pode avançar.")
    else:
        warnings.append("Todas as etapas didáticas foram verificadas.")
        warnings.append("Mesmo preparado, o executor continua sem enviar ordem.")
        warnings.append("A próxima etapa exigirá autorização separada antes de qualquer integração real com Testnet.")

    simulated_executor_order = {
        "symbol": plan.get("symbol"),
        "side": plan.get("side"),
        "order_type": plan.get("order_type"),
        "entry_price": plan.get("entry_price"),
        "quantity": plan.get("quantity"),
        "margin_usdt": plan.get("margin_usdt"),
        "leverage": plan.get("leverage"),
        "notional_usdt": plan.get("notional_usdt"),
        "partial_take_profit_price": plan.get("partial_take_profit_price"),
        "partial_close_percent": plan.get("partial_close_percent"),
        "invalidation_price": plan.get("invalidation_price"),
        "reduce_only_for_entry": False,
        "reduce_only_for_partial_exit": True,
    }

    return {
        "ok": True,
        "route": "/api/controlled-testnet-executor",
        "action": "CONTROLLED_TESTNET_EXECUTOR",
        "executor_type": "EXECUTOR_DIDATICO_TESTNET_CONTROLADO",
        "decision": decision,
        "executor_status": executor_status,
        "execution_status": execution_status,
        "environment": "BINANCE_FUTURES_TESTNET_CONTROLLED_SIMULATION",
        "symbol": plan.get("symbol"),
        "side": plan.get("side"),
        "order_type": plan.get("order_type"),
        "entry_price": plan.get("entry_price"),
        "quantity": plan.get("quantity"),
        "margin_usdt": plan.get("margin_usdt"),
        "leverage": plan.get("leverage"),
        "notional_usdt": plan.get("notional_usdt"),
        "partial_take_profit_price": plan.get("partial_take_profit_price"),
        "partial_close_percent": plan.get("partial_close_percent"),
        "invalidation_price": plan.get("invalidation_price"),
        "mec_decision": mec.get("decision"),
        "mec_direction": mec.get("direction"),
        "mec_confidence": mec.get("confidence"),
        "risk_decision": risk.get("decision"),
        "risk_level": risk.get("risk_level"),
        "human_confirmation": human.get("human_confirmation"),
        "manual_authorization": manual_auth.get("controlled_test_authorization"),
        "risk_engine_required": True,
        "manual_final_approval_required": True,
        "controlled_test_authorization": True,
        "trading_enabled": False,
        "testnet_orders_enabled": False,
        "real_orders_enabled": False,
        "send_order_to_binance": False,
        "simulated_executor_order": simulated_executor_order,
        "checks": checks,
        "blocks": blocks,
        "warnings": warnings,
        "safety_status": "EXECUTOR_DIDATICO_BLOQUEADO_PARA_ENVIO",
        "action_recommended": action_recommended,
        "next_step": next_step,
        "message": "Executor didático testnet controlado preparado. Nenhuma ordem foi enviada para a Binance.",
        "safety_note": "Esta etapa apenas organiza a lógica do executor. Não executa ordem real nem testnet.",
    }

def build_final_testnet_execution_authorization():
    """
    Autorização final para futura execução em Testnet real.
    Esta função NÃO envia ordem para a Binance.
    Ela apenas registra que o executor didático passou pelas travas anteriores
    e que uma nova autorização humana seria obrigatória antes de qualquer teste real.
    """
    executor = build_controlled_testnet_executor()

    checks = executor.get("checks", {})

    final_authorization_ready = all([
        bool(checks.get("human_confirmation_received", False)),
        bool(checks.get("manual_authorization_registered", False)),
        bool(checks.get("mec_decision_loaded", False)),
        bool(checks.get("mec_allows_plan", False)),
        bool(checks.get("safe_order_plan_loaded", False)),
        bool(checks.get("risk_final_validation_loaded", False)),
        bool(checks.get("testnet_simulation_loaded", False)),
        bool(executor.get("controlled_test_authorization", False) or checks.get("controlled_test_authorization", False)),
        bool(checks.get("trading_disabled", False)),
        bool(checks.get("testnet_orders_disabled", False)),
        bool(checks.get("real_orders_disabled", False)),
    ])

    warnings = [
        "Esta autorização final ainda não executa ordem.",
        "Ordens reais continuam desativadas.",
        "Ordens Testnet continuam desativadas nesta etapa.",
        "Qualquer integração futura com Testnet real exigirá executor separado, logs e nova autorização.",
    ]

    blocks = [
        "TRADING_ENABLED_FALSE",
        "TESTNET_ORDERS_ENABLED_FALSE",
        "REAL_ORDERS_ENABLED_FALSE",
        "FINAL_AUTHORIZATION_ONLY",
    ]

    decision = "AUTORIZACAO_FINAL_PREPARADA" if final_authorization_ready else "AUTORIZACAO_FINAL_BLOQUEADA"
    authorization_status = "PRONTA_PARA_PROXIMA_ETAPA_DIDATICA" if final_authorization_ready else "BLOQUEADA_POR_CHECKS_INCOMPLETOS"

    return {
        "ok": True,
        "route": "/api/final-testnet-execution-authorization",
        "action": "FINAL_TESTNET_EXECUTION_AUTHORIZATION",
        "execution_status": "NÃO EXECUTADO",
        "authorization_status": authorization_status,
        "decision": decision,
        "environment": "BINANCE_FUTURES_TESTNET_AUTHORIZATION_ONLY",

        "symbol": executor.get("symbol", "ETHUSDT"),
        "side": executor.get("side", "BUY"),
        "order_type": executor.get("order_type", "LIMIT"),
        "entry_price": executor.get("entry_price"),
        "quantity": executor.get("quantity"),
        "margin_usdt": executor.get("margin_usdt"),
        "leverage": executor.get("leverage"),
        "notional_usdt": executor.get("notional_usdt"),
        "partial_take_profit_price": executor.get("partial_take_profit_price"),
        "partial_close_percent": executor.get("partial_close_percent"),
        "invalidation_price": executor.get("invalidation_price"),

        "human_confirmation": True,
        "manual_authorization": True,
        "risk_engine_required": True,
        "manual_final_approval_required": True,
        "final_testnet_authorization": final_authorization_ready,

        "trading_enabled": False,
        "testnet_orders_enabled": False,
        "real_orders_enabled": False,
        "send_order_to_binance": False,

        "safety_status": "AUTORIZAÇÃO_FINAL_SEM_EXECUÇÃO",
        "next_step": "CRIAR_EXECUTOR_TESTNET_REAL_SEPARADO_COM_LOGS_E_NOVA_AUTORIZACAO",
        "message": "Autorização final didática preparada. Nenhuma ordem foi enviada para a Binance.",
        "safety_note": "Esta etapa apenas registra autorização final didática. Não executa ordem real nem testnet.",
        "warnings": warnings,
        "blocks": blocks,
        "checks": checks,
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
    <h2>🧠 Cérebro MEC — Decisão Operacional</h2>
    <p class="muted">
        Este bloco representa a inteligência central do robô: leitura do mercado,
        direção provável, confiança, risco e próxima ação. Nenhuma ordem é executada automaticamente.
    </p>

    <div class="grid">
        <div class="box">
            <strong>Ação:</strong><br>
            <span id="mec-action">Carregando...</span>
        </div>

        <div class="box">
            <strong>Objetivo:</strong><br>
            <span id="mec-objective">Carregando...</span>
        </div>

        <div class="box">
            <strong>Decisão:</strong><br>
            <span id="mec-decision">Carregando...</span>
        </div>

        <div class="box">
            <strong>Direção:</strong><br>
            <span id="mec-direction">Carregando...</span>
        </div>

        <div class="box">
            <strong>Confiança:</strong><br>
            <span id="mec-confidence">Carregando...</span>
        </div>

        <div class="box">
            <strong>Status do risco:</strong><br>
            <span id="mec-risk">Carregando...</span>
        </div>

        <div class="box">
            <strong>Preparar plano?</strong><br>
            <span id="mec-can-plan">Carregando...</span>
        </div>

        <div class="box">
            <strong>Próxima etapa:</strong><br>
            <span id="mec-next">Carregando...</span>
        </div>
    </div>

    <div class="alert" id="mec-entry">
        Carregando instrução de entrada...
    </div>

    <div class="alert" id="mec-warning">
        Carregando alertas operacionais...
    </div>
</div>

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
        <div class="card border-{% if binance_testnet.get('connected') %}green{% else %}red{% endif %}">
            <h2>Binance Futures Testnet</h2>

            {% if binance_testnet.get('connected') %}
                <span class="pill green">CONECTADO</span>
            {% else %}
                <span class="pill red">NÃO CONECTADO</span>
            {% endif %}

            <span class="pill blue">CORRETORA-ALVO: BINANCE FUTURES</span>
            <span class="pill red">EXECUÇÃO AUTOMÁTICA BLOQUEADA</span>

            <div class="grid">
                <div class="box col-3">
                    <strong>Ambiente:</strong><br>
                    {{ binance_testnet.get('environment', 'N/A') }}
                </div>

                <div class="box col-3">
                    <strong>API Key:</strong><br>
                    {% if binance_testnet.get('has_api_key') %}Detectada{% else %}Não detectada{% endif %}
                </div>

                <div class="box col-3">
                    <strong>Secret Key:</strong><br>
                    {% if binance_testnet.get('has_api_secret') %}Detectada{% else %}Não detectada{% endif %}
                </div>

                <div class="box col-3">
                    <strong>Testnet:</strong><br>
                    {{ binance_testnet.get('use_testnet') }}
                </div>

                <div class="box col-3">
                    <strong>Trading:</strong><br>
                    {{ binance_testnet.get('trading_enabled') }}
                </div>

                <div class="box col-3">
                    <strong>Human Confirm:</strong><br>
                    {{ binance_testnet.get('human_confirm_required') }}
                </div>

                <div class="box col-3">
                    <strong>Segurança:</strong><br>
                    {{ binance_testnet.get('safety_status', 'N/A') }}
                </div>

                <div class="box col-3">
                    <strong>Ordens:</strong><br>
                    {% if binance_testnet.get('orders_enabled_now') %}Liberadas{% else %}Bloqueadas{% endif %}
                </div>
            </div>

            <p><strong>Mensagem:</strong> {{ binance_testnet.get('message', 'Sem mensagem.') }}</p>

            {% if binance_testnet.get('balance') %}
                <div class="note">
                    <strong>Saldo USDT Testnet:</strong><br>
                    Saldo: {{ binance_testnet.get('balance', {}).get('balance', 0) }} |
                    Disponível: {{ binance_testnet.get('balance', {}).get('availableBalance', 0) }} |
                    Carteira: {{ binance_testnet.get('balance', {}).get('crossWalletBalance', 0) }}
                </div>
            {% endif %}

            {% if binance_testnet.get('positions') %}
                <div class="note">
                    <strong>Posições abertas:</strong>
                    {{ binance_testnet.get('positions', {}).get('count', 0) }}
                </div>
            {% endif %}

            {% if binance_testnet.get('open_orders') %}
                <div class="note">
                    <strong>Ordens abertas:</strong>
                    {{ binance_testnet.get('open_orders', {}).get('count', 0) }}
                </div>
            {% endif %}

            {% if not binance_testnet.get('connected') %}
                <div class="alert">
                    <strong>Atenção:</strong>
                    a Binance Futures Testnet está configurada, mas o servidor atual pode estar bloqueado pela Binance por restrição de localização.
                    Mesmo assim, as chaves foram detectadas e a execução automática continua bloqueada.
                </div>
            {% endif %}
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
            <h2>Proposta Segura da Ordem</h2>
            <p class="muted">
                Esta proposta é apenas um plano seguro. Nenhuma ordem é executada automaticamente.
            </p>

            <div class="grid">
                <div class="box col-3">
                    <strong>Ação:</strong><br>
                    <span id="op-action">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Execução:</strong><br>
                    <span id="op-execution">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Segurança:</strong><br>
                    <span id="op-safety">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Confirmação humana:</strong><br>
                    <span id="op-human">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Ativo:</strong><br>
                    <span id="op-symbol">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Direção:</strong><br>
                    <span id="op-side">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Tipo:</strong><br>
                    <span id="op-type">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Entrada:</strong><br>
                    <span id="op-entry">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Margem:</strong><br>
                    <span id="op-margin">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Alavancagem:</strong><br>
                    <span id="op-leverage">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Valor nocional:</strong><br>
                    <span id="op-notional">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Quantidade:</strong><br>
                    <span id="op-quantity">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Alvo parcial:</strong><br>
                    <span id="op-take-profit">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Saída parcial:</strong><br>
                    <span id="op-partial-close">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Invalidação:</strong><br>
                    <span id="op-invalidation">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Reduce Only parcial:</strong><br>
                    <span id="op-reduce-only">Carregando...</span>
                </div>
            </div>

            <div class="note" id="op-message">
                Carregando proposta segura da ordem...
            </div>
        </div>

        <div class="card">
            <h2>Confirmação Humana Segura</h2>
            <p class="muted">
                Esta confirmação apenas registra aprovação manual. Ela não envia ordem para a Binance.
            </p>

            <div class="grid">
                <div class="box col-3">
                    <strong>Ação:</strong><br>
                    <span id="hc-action">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Execução:</strong><br>
                    <span id="hc-execution">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Motor de risco:</strong><br>
                    <span id="hc-risk">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Segurança:</strong><br>
                    <span id="hc-safety">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Trading:</strong><br>
                    <span id="hc-trading">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Testnet:</strong><br>
                    <span id="hc-testnet">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Real:</strong><br>
                    <span id="hc-real">Carregando...</span>
                </div>

                <div class="box col-3">
                    <strong>Próxima etapa:</strong><br>
                    <span id="hc-next">Carregando...</span>
                </div>
            </div>

            <div class="alert" id="hc-message">
                Carregando confirmação humana segura...
            </div>
        </div>

<div class="card">
    <h2>Validação Final do Motor de Risco</h2>
    <p class="muted">
        Esta etapa confere se a proposta pode seguir para teste seguro. Mesmo aprovada,
        nenhuma ordem é enviada automaticamente.
    </p>

    <div class="grid">
        <div class="box">
            <strong>Ação:</strong><br>
            <span id="risk-action">Carregando...</span>
        </div>

        <div class="box">
            <strong>Decisão:</strong><br>
            <span id="risk-decision">Carregando...</span>
        </div>

        <div class="box">
            <strong>Status:</strong><br>
            <span id="risk-execution">Carregando...</span>
        </div>

        <div class="box">
            <strong>Segurança:</strong><br>
            <span id="risk-safety">Carregando...</span>
        </div>

        <div class="box">
            <strong>Nível de risco:</strong><br>
            <span id="risk-level">Carregando...</span>
        </div>

        <div class="box">
            <strong>Ativo:</strong><br>
            <span id="risk-symbol">Carregando...</span>
        </div>

        <div class="box">
            <strong>Direção:</strong><br>
            <span id="risk-side">Carregando...</span>
        </div>

        <div class="box">
            <strong>Entrada:</strong><br>
            <span id="risk-entry">Carregando...</span>
        </div>

        <div class="box">
            <strong>Invalidação:</strong><br>
            <span id="risk-invalidation">Carregando...</span>
        </div>

        <div class="box">
            <strong>Distância até invalidação:</strong><br>
            <span id="risk-distance">Carregando...</span>
        </div>

        <div class="box">
            <strong>Margem:</strong><br>
            <span id="risk-margin">Carregando...</span>
        </div>

        <div class="box">
            <strong>Alavancagem:</strong><br>
            <span id="risk-leverage">Carregando...</span>
        </div>

        <div class="box">
            <strong>Valor nocional:</strong><br>
            <span id="risk-notional">Carregando...</span>
        </div>

        <div class="box">
            <strong>Quantidade:</strong><br>
            <span id="risk-quantity">Carregando...</span>
        </div>

        <div class="box">
            <strong>Próxima etapa:</strong><br>
            <span id="risk-next-step">Carregando...</span>
        </div>

        <div class="box">
            <strong>Reduce Only parcial:</strong><br>
            <span id="risk-reduce-only">Carregando...</span>
        </div>
    </div>

    <div class="alert" id="risk-message">
        Carregando validação final do motor de risco...
    </div>

    <div class="alert" id="risk-blocks">
        Bloqueios: carregando...
    </div>

    <div class="alert" id="risk-warnings">
        Alertas: carregando...
    </div>
</div>

<script>
(function () {
    function setText(id, value) {
        var element = document.getElementById(id);
        if (!element) return;
        if (value === null || value === undefined || value === "") {
            element.innerText = "-";
        } else {
            element.innerText = value;
        }
    }

    function joinList(value) {
        if (!value || !Array.isArray(value) || value.length === 0) {
            return "Nenhum item encontrado.";
        }
        return value.join(" | ");
    }

    fetch("/api/risk-final-validation")
        .then(function (response) {
            return response.json();
        })
        .then(function (risk) {
            setText("risk-action", risk.action);
            setText("risk-decision", risk.decision);
            setText("risk-execution", risk.execution_status);
            setText("risk-safety", risk.safety_status);
            setText("risk-level", risk.risk_level);
            setText("risk-symbol", risk.symbol);
            setText("risk-side", risk.side);
            setText("risk-entry", risk.entry_price);
            setText("risk-invalidation", risk.invalidation_price);
            setText("risk-distance", String(risk.distance_to_invalidation_percent) + "%");
            setText("risk-margin", String(risk.margin_usdt) + " USDT");
            setText("risk-leverage", String(risk.leverage) + "x");
            setText("risk-notional", String(risk.notional_usdt) + " USDT");
            setText("risk-quantity", risk.quantity);
            setText("risk-next-step", risk.next_step);
            setText("risk-reduce-only", risk.reduce_only_for_partial_exit ? "Sim" : "Não");
            setText("risk-message", risk.message || risk.action_recommended);
            setText("risk-blocks", "Bloqueios: " + joinList(risk.blocks));
            setText("risk-warnings", "Alertas: " + joinList(risk.warnings));
        })
        .catch(function (error) {
            setText("risk-action", "ERRO");
            setText("risk-decision", "PAUSAR");
            setText("risk-execution", "NÃO EXECUTADO");
            setText("risk-safety", "BLOQUEADO PARA EXECUÇÃO");
            setText("risk-message", "Não foi possível carregar a validação final do motor de risco: " + error);
            setText("risk-blocks", "Bloqueios: falha ao consultar a rota.");
            setText("risk-warnings", "Alertas: revisar rota /api/risk-final-validation.");
        });
})();
</script>

<div class="card">
    <h2>Simulação Testnet Controlada</h2>
    <p class="muted">
        Esta etapa apenas prepara uma simulação didática em ambiente testnet.
        Nenhuma ordem é enviada automaticamente para a Binance.
    </p>

    <div class="grid">
        <div class="box">
            <strong>Ação:</strong><br>
            <span id="sim-action">Carregando...</span>
        </div>

        <div class="box">
            <strong>Status:</strong><br>
            <span id="sim-status">Carregando...</span>
        </div>

        <div class="box">
            <strong>Execução:</strong><br>
            <span id="sim-execution">Carregando...</span>
        </div>

        <div class="box">
            <strong>Segurança:</strong><br>
            <span id="sim-safety">Carregando...</span>
        </div>

        <div class="box">
            <strong>Ativo:</strong><br>
            <span id="sim-symbol">Carregando...</span>
        </div>

        <div class="box">
            <strong>Direção:</strong><br>
            <span id="sim-side">Carregando...</span>
        </div>

        <div class="box">
            <strong>Tipo:</strong><br>
            <span id="sim-type">Carregando...</span>
        </div>

        <div class="box">
            <strong>Entrada:</strong><br>
            <span id="sim-entry">Carregando...</span>
        </div>

        <div class="box">
            <strong>Margem:</strong><br>
            <span id="sim-margin">Carregando...</span>
        </div>

        <div class="box">
            <strong>Alavancagem:</strong><br>
            <span id="sim-leverage">Carregando...</span>
        </div>

        <div class="box">
            <strong>Valor nocional:</strong><br>
            <span id="sim-notional">Carregando...</span>
        </div>

        <div class="box">
            <strong>Quantidade:</strong><br>
            <span id="sim-quantity">Carregando...</span>
        </div>

        <div class="box">
            <strong>Take Profit parcial:</strong><br>
            <span id="sim-take-profit">Carregando...</span>
        </div>

        <div class="box">
            <strong>Saída parcial:</strong><br>
            <span id="sim-partial-close">Carregando...</span>
        </div>

        <div class="box">
            <strong>Invalidação:</strong><br>
            <span id="sim-invalidation">Carregando...</span>
        </div>

        <div class="box">
            <strong>Reduce Only parcial:</strong><br>
            <span id="sim-reduce-only">Carregando...</span>
        </div>
    </div>

    <div class="alert" id="sim-message">
        Carregando simulação testnet controlada...
    </div>

    <div class="alert" id="sim-warning">
        Nenhuma ordem será enviada automaticamente.
    </div>
</div>

<div class="card">
    <h2>Executor Didático Testnet Controlado</h2>
    <p class="muted">
        Esta etapa verifica se o executor didático está preparado, mas continua sem enviar ordem para a Binance.
    </p>

    <div class="grid">
        <div class="box">
            <strong>Ação:</strong><br>
            <span id="exec-action">Carregando...</span>
        </div>

        <div class="box">
            <strong>Tipo:</strong><br>
            <span id="exec-type">Carregando...</span>
        </div>

        <div class="box">
            <strong>Decisão:</strong><br>
            <span id="exec-decision">Carregando...</span>
        </div>

        <div class="box">
            <strong>Status:</strong><br>
            <span id="exec-status">Carregando...</span>
        </div>

        <div class="box">
            <strong>Execução:</strong><br>
            <span id="exec-execution">Carregando...</span>
        </div>

        <div class="box">
            <strong>Enviar Binance?</strong><br>
            <span id="exec-send">Carregando...</span>
        </div>

        <div class="box">
            <strong>Trading:</strong><br>
            <span id="exec-trading">Carregando...</span>
        </div>

        <div class="box">
            <strong>Testnet Orders:</strong><br>
            <span id="exec-testnet">Carregando...</span>
        </div>

        <div class="box">
            <strong>Real Orders:</strong><br>
            <span id="exec-real">Carregando...</span>
        </div>

        <div class="box">
            <strong>Símbolo:</strong><br>
            <span id="exec-symbol">Carregando...</span>
        </div>

        <div class="box">
            <strong>Direção:</strong><br>
            <span id="exec-side">Carregando...</span>
        </div>

        <div class="box">
            <strong>Quantidade:</strong><br>
            <span id="exec-quantity">Carregando...</span>
        </div>
    </div>

    <div class="alert" id="exec-message">
        Carregando executor didático testnet controlado...
    </div>

    <div class="alert" id="exec-warning">
        Nenhuma ordem será enviada automaticamente.
    </div>
</div>

        <div class="card">
            <h2>Segurança Operacional</h2>

            <p>
                Este painel é apenas educacional. Ele não envia ordem automática,
                não executa compra ou venda e mantém qualquer operação bloqueada
                enquanto não houver confirmação humana e validação final do motor de risco.
            </p>

            <div class="alert">
                Regra central: preservar capital vem antes de qualquer oportunidade.
            </div>
        </div>

        <p class="muted">
            Links rápidos:
            <a href="/api/report">API JSON</a> |
            <a href="/api/binance-testnet">Binance Testnet</a> |
            <a href="/api/order-plan">Plano de Ordem</a> |
            <a href="/api/human-confirm">Confirmação Humana</a> |
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

        function yesNo(value) {
            return value ? "Sim" : "Não";
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

function loadMecDecisionEngine() {
    fetch("/api/mec-decision-engine")
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            setText("mec-action", data.action || "-");
            setText("mec-objective", data.objective || "-");
            setText("mec-decision", data.decision || "-");
            setText("mec-direction", data.direction || "-");
            setText("mec-confidence", data.confidence || "-");
            setText("mec-risk", data.risk_status || "-");
            setText("mec-can-plan", data.can_prepare_order_plan ? "Sim" : "Não");
            setText("mec-next", data.next_step || "-");

            setText("mec-entry", data.entry_instruction || "Sem instrução de entrada.");

            var warnings = data.warnings || [];
            if (warnings.length > 0) {
                setText("mec-warning", warnings.join(" | "));
            } else {
                setText("mec-warning", "Nenhum alerta operacional encontrado.");
            }
        })
        .catch(function (error) {
            setText("mec-action", "ERRO");
            setText("mec-decision", "ERRO AO CARREGAR");
            setText("mec-direction", "-");
            setText("mec-confidence", "-");
            setText("mec-risk", "-");
            setText("mec-can-plan", "Não");
            setText("mec-next", "-");
            setText("mec-entry", "Não foi possível carregar o Cérebro MEC: " + error);
            setText("mec-warning", "Análise operacional permaneceu bloqueada por segurança.");
        });
}

        function loadHumanConfirm() {
            fetch("/api/human-confirm")
                .then(function (response) {
                    return response.json();
                })
                .then(function (data) {
                    setText("hc-action", data.action || "-");
                    setText("hc-execution", data.execution_status || "NÃO EXECUTADO");
                    setText("hc-risk", data.risk_engine_required ? "Obrigatório" : "Não");
                    setText("hc-safety", data.safety_status || "BLOQUEADO PARA EXECUÇÃO");
                    setText("hc-trading", yesNo(data.trading_enabled));
                    setText("hc-testnet", yesNo(data.testnet_orders_enabled));
                    setText("hc-real", yesNo(data.real_orders_enabled));
                    setText("hc-next", data.next_step || "-");
                    setText("hc-message", data.safety_note || data.message || "Confirmação humana segura carregada.");
                })
                .catch(function (error) {
                    setText("hc-action", "ERRO");
                    setText("hc-execution", "NÃO EXECUTADO");
                    setText("hc-safety", "BLOQUEADO PARA EXECUÇÃO");
                    setText("hc-message", "Não foi possível carregar a confirmação humana segura: " + error);
                });
        }

function loadTestnetSimulation() {
    fetch("/api/testnet-simulation")
        .then(function(response) {
            return response.json();
        })
        .then(function(data) {
            const simulated = data.simulated_order || {};

            setText("sim-action", data.action || "-");
            setText("sim-status", data.simulation_status || "-");
            setText("sim-execution", data.execution_status || "-");
            setText("sim-safety", data.safety_status || "-");

            setText("sim-symbol", simulated.symbol || data.symbol || "-");
            setText("sim-side", simulated.side || data.side || "-");
            setText("sim-type", simulated.order_type || data.order_type || "-");
            setText("sim-entry", simulated.entry_price || data.entry_price || "-");

            setText("sim-margin", String(simulated.margin_usdt || data.margin_usdt || "-") + " USDT");
            setText("sim-leverage", String(simulated.leverage || data.leverage || "-") + "x");
            setText("sim-notional", String(simulated.notional_usdt || data.notional_usdt || "-") + " USDT");
            setText("sim-quantity", simulated.quantity || data.quantity || "-");

            setText("sim-take-profit", simulated.partial_take_profit_price || data.partial_take_profit_price || "-");
            setText("sim-partial-close", String(data.partial_close_percent || "-") + "%");
            setText("sim-invalidation", simulated.invalidation_price || data.invalidation_price || "-");
            setText("sim-reduce-only", simulated.reduce_only_for_partial_exit ? "Sim" : "Não");

            setText("sim-message", data.message || "Simulação testnet controlada carregada.");
            setText("sim-warning", data.safety_note || "Nenhuma ordem será enviada automaticamente.");
        })
        .catch(function(error) {
            setText("sim-action", "ERRO");
            setText("sim-status", "ERRO AO CARREGAR");
            setText("sim-execution", "NÃO EXECUTADO");
            setText("sim-safety", "BLOQUEADO PARA EXECUÇÃO");
            setText("sim-message", "Não foi possível carregar a simulação testnet: " + error);
            setText("sim-warning", "A simulação permaneceu bloqueada por segurança.");
        });
}

function loadControlledTestnetExecutor() {
    fetch("/api/controlled-testnet-executor")
        .then(function (response) {
            return response.json();
        })
        .then(function (data) {
            setText("exec-action", data.action || "-");
            setText("exec-type", data.executor_type || "-");
            setText("exec-decision", data.decision || "-");
            setText("exec-status", data.executor_status || "-");
            setText("exec-execution", data.execution_status || "NÃO EXECUTADO");
            setText("exec-send", data.send_order_to_binance ? "Sim" : "Não");
            setText("exec-trading", data.trading_enabled ? "Sim" : "Não");
            setText("exec-testnet", data.testnet_orders_enabled ? "Sim" : "Não");
            setText("exec-real", data.real_orders_enabled ? "Sim" : "Não");
            setText("exec-symbol", data.symbol || "-");
            setText("exec-side", data.side || "-");
            setText("exec-quantity", data.quantity || "-");

            setText("exec-message", data.message || "Executor didático carregado.");

            var warnings = data.warnings || [];
            if (warnings.length > 0) {
                setText("exec-warning", warnings.join(" | "));
            } else {
                setText("exec-warning", "Nenhum alerta operacional encontrado.");
            }
        })
        .catch(function (error) {
            setText("exec-action", "ERRO");
            setText("exec-type", "ERRO AO CARREGAR");
            setText("exec-decision", "BLOQUEADO");
            setText("exec-status", "BLOQUEADO POR SEGURANÇA");
            setText("exec-execution", "NÃO EXECUTADO");
            setText("exec-send", "Não");
            setText("exec-trading", "Não");
            setText("exec-testnet", "Não");
            setText("exec-real", "Não");
            setText("exec-symbol", "-");
            setText("exec-side", "-");
            setText("exec-quantity", "-");
            setText("exec-message", "Não foi possível carregar o executor didático: " + error);
            setText("exec-warning", "Executor permaneceu bloqueado por segurança.");
        });
}

        loadMecDecisionEngine();
        loadOrderPlan();
        loadHumanConfirm();
        loadTestnetSimulation();
loadControlledTestnetExecutor();
    </script>
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
            <p><a href="/api/binance-testnet">Ver Binance Testnet</a></p>
            <p><a href="/api/order-plan">Ver Plano de Ordem</a></p>
            <p><a href="/api/human-confirm">Ver Confirmação Humana</a></p>
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
        binance_testnet=report["binance_testnet"],
        top_opportunities=report["top_opportunities"],
        setup_radar=report["setup_radar"],
        assets=report["assets"],
    )


@app.route("/api/report")
def api_report():
    return jsonify(build_report())


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
                "real_orders_enabled": False,
            }
        )


@app.route("/api/order-plan")
def api_order_plan():
    return jsonify(build_safe_order_plan())


@app.route("/api/human-confirm")
def api_human_confirm():
    return jsonify(build_human_confirmation())

@app.route("/api/risk-final-validation")
def api_risk_final_validation():
    return jsonify(build_risk_final_validation())

@app.route("/api/testnet-simulation")
def api_testnet_simulation():
    return jsonify(build_testnet_simulation())

@app.route("/api/manual-test-authorization")
def api_manual_test_authorization():
    return jsonify(build_manual_test_authorization())

@app.route("/api/controlled-testnet-executor")
def api_controlled_testnet_executor():
    return jsonify(build_controlled_testnet_executor())


@app.route("/api/final-testnet-execution-authorization")
def api_final_testnet_execution_authorization():
    return jsonify(build_final_testnet_execution_authorization())

@app.route("/api/mec-decision-engine")
def api_mec_decision_engine():
    return jsonify(build_mec_decision_engine())

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