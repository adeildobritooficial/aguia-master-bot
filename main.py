# main.py

from datetime import datetime

from config import (
    FALLBACK_SYMBOLS,
    USE_AUTO_SYMBOL_SELECTION,
    MAX_AUTO_SYMBOLS,
    TIMEFRAME_4H,
    TIMEFRAME_5M,
    LIMIT_4H,
    LIMIT_5M,
)

from exchange_binance import (
    get_klines,
    get_current_price,
    get_top_usdt_symbols,
)

from market_analyzer import analyze_market_structure
from strategy_mec import evaluate_entry, evaluate_3x_scenario
from risk_engine import evaluate_account_risk
from logger import log_event


def get_symbols_to_analyze() -> list[str]:
    """
    Define quais ativos serão analisados no ciclo.

    Prioriza seleção automática por volume.
    Se falhar, usa lista fixa de segurança.
    """
    if not USE_AUTO_SYMBOL_SELECTION:
        return FALLBACK_SYMBOLS

    try:
        symbols = get_top_usdt_symbols(limit=MAX_AUTO_SYMBOLS)

        if symbols:
            return symbols

    except Exception as error:
        log_event(
            "FALHA NA SELEÇÃO AUTOMÁTICA DE ATIVOS",
            "Não foi possível buscar ativos por volume. Usando lista fallback.",
            {
                "erro": str(error),
                "fallback": ", ".join(FALLBACK_SYMBOLS),
            },
        )

    return FALLBACK_SYMBOLS


def analyze_symbol(symbol: str, btc_context: dict | None = None) -> dict:
    """
    Analisa um ativo individual em 4H e 5M.
    Retorna a decisão do robô observador.
    """

    df_4h = get_klines(symbol, TIMEFRAME_4H, LIMIT_4H)
    df_5m = get_klines(symbol, TIMEFRAME_5M, LIMIT_5M)

    market_data = analyze_market_structure(df_4h, df_5m)
    current_price = get_current_price(symbol)

    entry_decision = evaluate_entry(
        symbol=symbol,
        market_data=market_data,
        btc_context=btc_context if symbol != "BTCUSDT" else None,
    )

    return {
        "symbol": symbol,
        "current_price": current_price,
        "market_data": market_data,
        "entry_decision": entry_decision,
    }


def build_observer_report() -> dict:
    """
    Executa o ciclo observador e retorna um relatório estruturado.
    Esta função é usada pela API /run e /dashboard.

    Nenhuma ordem é executada.
    """

    cycle_results = []

    symbols_to_analyze = get_symbols_to_analyze()

    btc_symbol = "BTCUSDT"

    btc_4h = get_klines(btc_symbol, TIMEFRAME_4H, LIMIT_4H)
    btc_5m = get_klines(btc_symbol, TIMEFRAME_5M, LIMIT_5M)
    btc_context = analyze_market_structure(btc_4h, btc_5m)
    btc_price = get_current_price(btc_symbol)

    btc_summary = {
        "symbol": btc_symbol,
        "price": btc_price,
        "candle_4h": btc_context["last_4h_candle"]["direction"],
        "candle_5m": btc_context["last_5m_candle"]["direction"],
        "volume_5m": btc_context["volume_5m"]["status"],
        "support_4h": btc_context["support_resistance_4h"]["support"],
        "resistance_4h": btc_context["support_resistance_4h"]["resistance"],
        "near_support_4h": btc_context["near_support"],
        "near_resistance_4h": btc_context["near_resistance"],
    }

    for symbol in symbols_to_analyze:
        try:
            result = analyze_symbol(
                symbol=symbol,
                btc_context=btc_context,
            )

            decision = result["entry_decision"]
            market_data = result["market_data"]

            cycle_results.append(
                {
                    "symbol": symbol,
                    "price": result["current_price"],
                    "decision": decision["decision"],
                    "direction": decision["direction"],
                    "confidence": decision["confidence"],
                    "candle_4h": market_data["last_4h_candle"]["direction"],
                    "candle_5m": market_data["last_5m_candle"]["direction"],
                    "volume_5m": market_data["volume_5m"]["status"],
                    "support_4h": decision["support"],
                    "resistance_4h": decision["resistance"],
                    "distance_to_support_percent": decision["distance_to_support_percent"],
                    "distance_to_resistance_percent": decision["distance_to_resistance_percent"],
                    "reasons": decision["reasons"],
                    "warnings": decision["warnings"],
                }
            )

        except Exception as error:
            cycle_results.append(
                {
                    "symbol": symbol,
                    "price": None,
                    "decision": "ERRO",
                    "direction": "NONE",
                    "confidence": "BAIXA",
                    "candle_4h": "N/A",
                    "candle_5m": "N/A",
                    "volume_5m": "N/A",
                    "support_4h": None,
                    "resistance_4h": None,
                    "distance_to_support_percent": None,
                    "distance_to_resistance_percent": None,
                    "reasons": [
                        "Erro ao analisar este ativo.",
                        str(error),
                    ],
                    "warnings": [
                        "Ativo ignorado neste ciclo.",
                    ],
                }
            )

    risk_test = evaluate_account_risk(
        balance_usdt=1000,
        current_risk_percent=4.5,
        open_positions=3,
        planned_margin_usdt=25,
        leverage=20,
        liquidation_price=2850,
        invalidation_price=2900,
        direction="LONG",
    )

    eth_4h = get_klines("ETHUSDT", TIMEFRAME_4H, LIMIT_4H)
    eth_5m = get_klines("ETHUSDT", TIMEFRAME_5M, LIMIT_5M)
    eth_market_data = analyze_market_structure(eth_4h, eth_5m)

    x3_test = evaluate_3x_scenario(
        position_side="LONG",
        market_data=eth_market_data,
        candles_4h_against=8,
    )

    return {
        "status": "success",
        "bot": "ÁGUIA MASTER BOT",
        "mode": "OBSERVER",
        "environment": "BINANCE FUTURES TESTNET / PUBLIC DATA",
        "orders_executed": False,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "symbol_selection": {
            "automatic": USE_AUTO_SYMBOL_SELECTION,
            "max_symbols": MAX_AUTO_SYMBOLS,
            "symbols_analyzed": symbols_to_analyze,
        },
        "btc_context": btc_summary,
        "summary": cycle_results,
        "risk": {
            "status": risk_test["status"],
            "balance_usdt": risk_test["balance_usdt"],
            "current_risk_percent": risk_test["current_risk_percent"],
            "open_positions": risk_test["open_positions"],
            "planned_margin_usdt": risk_test["planned_margin_usdt"],
            "margin_percent": risk_test["margin_percent"],
            "leverage": risk_test["leverage"],
            "notional_exposure": risk_test["notional_exposure"],
            "reasons": risk_test["reasons"],
            "warnings": risk_test["warnings"],
        },
        "x3": {
            "status": x3_test["status"],
            "candles_4h_against": x3_test["candles_4h_against"],
            "reasons": x3_test["reasons"],
            "warnings": x3_test["warnings"],
            "reduce_only_rule": x3_test["reduce_only_rule"],
            "note": "Este 3X é apenas teste educacional. Não representa posição real aberta.",
        },
        "safety": {
            "api_keys_used": False,
            "real_orders_enabled": False,
            "testnet_orders_enabled": False,
            "message": "Nenhuma ordem é executada nesta fase. O robô apenas observa e analisa.",
        },
    }


def run_observer() -> dict:
    """
    Executa o robô observador, gera logs no terminal e retorna relatório.
    """

    log_event(
        "INÍCIO DO ROBÔ OBSERVADOR",
        "ÁGUIA MASTER BOT iniciado em modo observador. Nenhuma ordem será executada.",
        {
            "modo": "OBSERVER",
            "ambiente": "PUBLIC_MARKET_DATA / BINANCE FUTURES TESTNET",
            "seleção_de_ativos": "AUTOMÁTICA" if USE_AUTO_SYMBOL_SELECTION else "FALLBACK",
            "máximo_de_ativos": MAX_AUTO_SYMBOLS,
        },
    )

    try:
        report = build_observer_report()

        for item in report["summary"]:
            log_event(
                "DECISÃO DE ENTRADA",
                f"Resultado da análise inicial para {item['symbol']}.",
                {
                    "ativo": item["symbol"],
                    "preço_atual": item["price"],
                    "decisão": item["decision"],
                    "direção": item["direction"],
                    "confiança": item["confidence"],
                    "candle_4h": item["candle_4h"],
                    "candle_5m": item["candle_5m"],
                    "volume_5m": item["volume_5m"],
                    "suporte_4h": item["support_4h"],
                    "resistência_4h": item["resistance_4h"],
                    "distância_suporte_%": item["distance_to_support_percent"],
                    "distância_resistência_%": item["distance_to_resistance_percent"],
                    "motivos": " | ".join(item["reasons"]),
                    "alertas": " | ".join(item["warnings"]),
                },
            )

        log_event(
            "FIM DO CICLO",
            "Ciclo de observação concluído. Nenhuma ordem foi executada.",
        )

        return report

    except Exception as error:
        log_event(
            "ERRO NO CICLO",
            "O robô encontrou um erro e interrompeu o ciclo com segurança.",
            {
                "erro": str(error),
                "ação": "PAUSAR / NÃO EXECUTAR",
            },
        )

        return {
            "status": "error",
            "orders_executed": False,
            "error": str(error),
            "message": "O robô encontrou um erro e não executou nenhuma ordem.",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


if __name__ == "__main__":
    run_observer()