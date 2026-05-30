# main.py

from config import (
    SYMBOLS,
    TIMEFRAME_4H,
    TIMEFRAME_5M,
    LIMIT_4H,
    LIMIT_5M,
)

from exchange_binance import get_klines, get_current_price
from market_analyzer import analyze_market_structure
from strategy_mec import evaluate_entry, evaluate_3x_scenario
from risk_engine import evaluate_account_risk
from logger import log_event


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


def run_observer():
    """
    ÁGUIA MASTER BOT — MVP 1

    Modo atual:
    - observador;
    - dados públicos;
    - sem API Key;
    - sem execução de ordens;
    - sem conta real;
    - análise educacional baseada nas primeiras regras do MEC.
    """

    cycle_results = []

    log_event(
        "INÍCIO DO ROBÔ OBSERVADOR",
        "ÁGUIA MASTER BOT iniciado em modo observador. Nenhuma ordem será executada.",
        {
            "modo": "OBSERVER",
            "ambiente": "PUBLIC_MARKET_DATA / BINANCE FUTURES TESTNET",
            "ativos": ", ".join(SYMBOLS),
        },
    )

    try:
        # 1. BTC como contexto principal
        btc_symbol = "BTCUSDT"

        log_event(
            "COLETA BTC",
            "Coletando candles do BTC para contexto geral de mercado.",
        )

        btc_4h = get_klines(btc_symbol, TIMEFRAME_4H, LIMIT_4H)
        btc_5m = get_klines(btc_symbol, TIMEFRAME_5M, LIMIT_5M)
        btc_context = analyze_market_structure(btc_4h, btc_5m)
        btc_price = get_current_price(btc_symbol)

        log_event(
            "CONTEXTO BTC",
            "Contexto inicial do Bitcoin coletado.",
            {
                "ativo": btc_symbol,
                "preço_atual": btc_price,
                "candle_4h": btc_context["last_4h_candle"]["direction"],
                "candle_5m": btc_context["last_5m_candle"]["direction"],
                "volume_5m": btc_context["volume_5m"]["status"],
                "suporte_4h": btc_context["support_resistance_4h"]["support"],
                "resistência_4h": btc_context["support_resistance_4h"]["resistance"],
                "perto_suporte_4h": btc_context["near_support"],
                "perto_resistência_4h": btc_context["near_resistance"],
            },
        )

        # 2. Análise dos ativos
        for symbol in SYMBOLS:
            log_event(
                "ANÁLISE DE ATIVO",
                f"Iniciando análise de {symbol}.",
            )

            result = analyze_symbol(
                symbol=symbol,
                btc_context=btc_context,
            )

            decision = result["entry_decision"]
            market_data = result["market_data"]

            cycle_results.append(
                {
                    "ativo": symbol,
                    "preço": result["current_price"],
                    "decisão": decision["decision"],
                    "direção": decision["direction"],
                    "confiança": decision["confidence"],
                    "suporte": decision["support"],
                    "resistência": decision["resistance"],
                    "distância_suporte_%": decision["distance_to_support_percent"],
                    "distância_resistência_%": decision["distance_to_resistance_percent"],
                    "candle_4h": market_data["last_4h_candle"]["direction"],
                    "candle_5m": market_data["last_5m_candle"]["direction"],
                    "volume_5m": market_data["volume_5m"]["status"],
                    "motivos": " | ".join(decision["reasons"]),
                    "alertas": " | ".join(decision["warnings"]),
                }
            )

            log_event(
                "DECISÃO DE ENTRADA",
                f"Resultado da análise inicial para {symbol}.",
                {
                    "ativo": symbol,
                    "preço_atual": result["current_price"],
                    "decisão": decision["decision"],
                    "direção": decision["direction"],
                    "confiança": decision["confidence"],
                    "candle_4h": market_data["last_4h_candle"]["direction"],
                    "candle_5m": market_data["last_5m_candle"]["direction"],
                    "volume_5m": market_data["volume_5m"]["status"],
                    "suporte_4h": decision["support"],
                    "resistência_4h": decision["resistance"],
                    "distância_suporte_%": decision["distance_to_support_percent"],
                    "distância_resistência_%": decision["distance_to_resistance_percent"],
                    "motivos": " | ".join(decision["reasons"]),
                    "alertas": " | ".join(decision["warnings"]),
                },
            )

        # 3. Teste educacional do motor de risco
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

        log_event(
            "TESTE DO MOTOR DE RISCO",
            "Validação educacional do Risk Engine com cenário padrão.",
            {
                "status": risk_test["status"],
                "banca": risk_test["balance_usdt"],
                "risco_atual_%": risk_test["current_risk_percent"],
                "operações_abertas": risk_test["open_positions"],
                "margem_%": risk_test["margin_percent"],
                "exposição_nominal": risk_test["notional_exposure"],
                "motivos": " | ".join(risk_test["reasons"]),
                "alertas": " | ".join(risk_test["warnings"]),
            },
        )

        # 4. Teste educacional da lógica 3X em ETH
        eth_4h = get_klines("ETHUSDT", TIMEFRAME_4H, LIMIT_4H)
        eth_5m = get_klines("ETHUSDT", TIMEFRAME_5M, LIMIT_5M)
        eth_market_data = analyze_market_structure(eth_4h, eth_5m)

        x3_test = evaluate_3x_scenario(
            position_side="LONG",
            market_data=eth_market_data,
            candles_4h_against=8,
        )

        log_event(
            "TESTE EDUCACIONAL 3X",
            "Validação inicial da lógica de alerta 3X. Nenhuma ordem será executada.",
            {
                "status": x3_test["status"],
                "candles_4h_contra": x3_test["candles_4h_against"],
                "motivos": " | ".join(x3_test["reasons"]),
                "alertas": " | ".join(x3_test["warnings"]),
                "regra_reduce_only": x3_test["reduce_only_rule"],
            },
        )

        # 5. Resumo final limpo
        print("\n\n" + "#" * 80)
        print("RESUMO FINAL DO CICLO — ÁGUIA MASTER BOT")
        print("#" * 80)

        for item in cycle_results:
            print(f"\nATIVO: {item['ativo']}")
            print(f"PREÇO: {item['preço']}")
            print(f"DECISÃO: {item['decisão']}")
            print(f"DIREÇÃO: {item['direção']}")
            print(f"CONFIANÇA: {item['confiança']}")
            print(f"CANDLE 4H: {item['candle_4h']}")
            print(f"CANDLE 5M: {item['candle_5m']}")
            print(f"VOLUME 5M: {item['volume_5m']}")
            print(f"SUPORTE 4H: {item['suporte']}")
            print(f"RESISTÊNCIA 4H: {item['resistência']}")
            print(f"DISTÂNCIA DO SUPORTE: {item['distância_suporte_%']}%")
            print(f"DISTÂNCIA DA RESISTÊNCIA: {item['distância_resistência_%']}%")
            print(f"MOTIVOS: {item['motivos']}")
            print(f"ALERTAS: {item['alertas']}")

        print("\nRISCO EDUCACIONAL:")
        print(f"STATUS: {risk_test['status']}")
        print(f"MOTIVOS: {' | '.join(risk_test['reasons'])}")
        print(f"ALERTAS: {' | '.join(risk_test['warnings'])}")

        print("\n3X EDUCACIONAL:")
        print(f"STATUS: {x3_test['status']}")
        print(f"MOTIVOS: {' | '.join(x3_test['reasons'])}")
        print(f"ALERTAS: {' | '.join(x3_test['warnings'])}")
        print(f"REDUCE ONLY: {x3_test['reduce_only_rule']}")

        print("\nAÇÃO DO ROBÔ:")
        print("Nenhuma ordem executada. Modo observador ativo.")

        print("#" * 80 + "\n")

        log_event(
            "FIM DO CICLO",
            "Ciclo de observação concluído. Nenhuma ordem foi executada.",
        )

    except Exception as error:
        log_event(
            "ERRO NO CICLO",
            "O robô encontrou um erro e interrompeu o ciclo com segurança.",
            {
                "erro": str(error),
                "ação": "PAUSAR / NÃO EXECUTAR",
            },
        )


if __name__ == "__main__":
    run_observer()