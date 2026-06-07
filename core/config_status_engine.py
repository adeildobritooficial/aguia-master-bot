# core/config_status_engine.py

"""
ÁGUIA MASTER BOT — Config Status Engine

Este módulo centraliza a leitura segura das configurações operacionais do robô.

IMPORTANTE:
- Não executa ordens.
- Não consulta corretora.
- Não altera posição.
- Apenas organiza o status das configurações para dashboard, APIs e relatórios.
"""

import os

from config import (
    BOT_MODE,
    EXCHANGE,
    ENVIRONMENT,
    USE_AUTO_SYMBOL_SELECTION,
    MAX_AUTO_SYMBOLS,
    MIN_SYMBOLS_REQUIRED,
    USE_OPERATIONAL_WHITELIST,
    TIMEFRAME_4H,
    TIMEFRAME_5M,
    MAX_RISK_PERCENT,
    BLOCK_RISK_PERCENT,
    KILL_SWITCH_RISK_PERCENT,
    ENABLE_3X_ANALYSIS,
    REQUIRE_REDUCE_ONLY_ON_EXITS,
)


def env_bool(name: str, default: bool = False) -> bool:
    """
    Lê variável de ambiente como booleano.
    """
    value = os.getenv(name)

    if value is None:
        return default

    return str(value).strip().lower() in ["1", "true", "yes", "sim", "on"]


def build_config_status() -> dict:
    """
    Monta um resumo seguro das configurações atuais do robô.
    """

    trading_enabled = env_bool("TRADING_ENABLED", False)
    real_trading_enabled = env_bool("REAL_TRADING_ENABLED", False)
    human_confirm_required = env_bool("HUMAN_CONFIRM_REQUIRED", True)
    binance_use_testnet = env_bool("BINANCE_USE_TESTNET", True)

    operation_target = os.getenv("OPERATION_TARGET", "BINANCE_FUTURES_TESTNET")

    safety_warnings = []
    safety_blockers = []

    if trading_enabled:
        safety_warnings.append("TRADING_ENABLED está true. Validar se isso é intencional.")

    if real_trading_enabled:
        safety_blockers.append("REAL_TRADING_ENABLED está true. Real deve permanecer bloqueado nesta fase.")

    if not human_confirm_required:
        safety_blockers.append("HUMAN_CONFIRM_REQUIRED está false. Confirmação humana deve permanecer obrigatória.")

    if not binance_use_testnet:
        safety_blockers.append("BINANCE_USE_TESTNET está false. Isso pode indicar ambiente real.")

    if operation_target != "BINANCE_FUTURES_TESTNET":
        safety_warnings.append("OPERATION_TARGET diferente de BINANCE_FUTURES_TESTNET. Validar antes de avançar.")

    if not safety_blockers:
        config_safety_status = "CONFIG_SEGURA"
    else:
        config_safety_status = "CONFIG_BLOQUEADA"

    return {
        "config_safety_status": config_safety_status,
        "bot_mode": BOT_MODE,
        "exchange": EXCHANGE,
        "environment": ENVIRONMENT,
        "operation_target": operation_target,
        "binance_use_testnet": binance_use_testnet,
        "trading_enabled": trading_enabled,
        "real_trading_enabled": real_trading_enabled,
        "human_confirm_required": human_confirm_required,
        "auto_symbol_selection": {
            "enabled": USE_AUTO_SYMBOL_SELECTION,
            "max_symbols": MAX_AUTO_SYMBOLS,
            "min_symbols_required": MIN_SYMBOLS_REQUIRED,
            "operational_whitelist_enabled": USE_OPERATIONAL_WHITELIST,
        },
        "timeframes": {
            "context": TIMEFRAME_4H,
            "trigger": TIMEFRAME_5M,
        },
        "risk_limits": {
            "max_risk_percent": MAX_RISK_PERCENT,
            "block_risk_percent": BLOCK_RISK_PERCENT,
            "kill_switch_risk_percent": KILL_SWITCH_RISK_PERCENT,
        },
        "x3": {
            "analysis_enabled": ENABLE_3X_ANALYSIS,
            "automatic_execution_enabled": False,
            "message": "3X permanece apenas em análise/simulação. Nunca automático nesta fase.",
        },
        "reduce_only": {
            "required_on_exits": REQUIRE_REDUCE_ONLY_ON_EXITS,
            "message": "Saídas parciais e fechamentos devem exigir Reduce Only.",
        },
        "safety_blockers": safety_blockers,
        "safety_warnings": safety_warnings,
        "message": "Config Status Engine ativo. Nenhuma ordem é executada por este módulo.",
    }