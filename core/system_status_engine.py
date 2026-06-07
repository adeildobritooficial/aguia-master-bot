# core/system_status_engine.py

"""
ÁGUIA MASTER BOT — System Status Engine

Este módulo consolida o status geral do robô.

IMPORTANTE:
- Não executa ordens.
- Não consulta corretora.
- Não altera posição.
- Apenas junta os status de segurança e configuração.
"""

from core.safety_status_engine import build_safety_status
from core.config_status_engine import build_config_status


def build_system_status() -> dict:
    """
    Monta um status geral do sistema usando os módulos seguros já criados.
    """

    safety = build_safety_status(
        trading_enabled=False,
        real_orders_enabled=False,
        testnet_orders_enabled=False,
        human_confirm_required=True,
        environment="BINANCE_FUTURES_TESTNET",
    )

    config = build_config_status()

    orders_blocked = (
        safety.get("trading_enabled") is False
        and safety.get("real_orders_enabled") is False
        and safety.get("testnet_orders_enabled") is False
    )

    config_safe = config.get("config_safety_status") == "CONFIG_SEGURA"
    safety_blocked = safety.get("status") == "SEGURO_BLOQUEADO"

    if orders_blocked and config_safe and safety_blocked:
        system_status = "ONLINE_SEGURO"
    else:
        system_status = "ATENCAO_VALIDAR_CONFIGURACAO"

    return {
        "system_status": system_status,
        "bot": "ÁGUIA MASTER BOT",
        "environment": "BINANCE_FUTURES_TESTNET",
        "orders_blocked": orders_blocked,
        "real_blocked": safety.get("real_orders_enabled") is False,
        "testnet_blocked": safety.get("testnet_orders_enabled") is False,
        "human_confirm_required": safety.get("human_confirm_required") is True,
        "config_safety_status": config.get("config_safety_status"),
        "safety_status": safety.get("status"),
        "config": config,
        "safety": safety,
        "message": "System Status Engine ativo. Nenhuma ordem é executada por este módulo.",
    }