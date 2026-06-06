# core/safety_status_engine.py

"""
ÁGUIA MASTER BOT — Safety Status Engine

Este módulo centraliza mensagens e estados de segurança operacional.

IMPORTANTE:
- Não executa ordens.
- Não consulta corretora.
- Não altera posição.
- Apenas organiza status de segurança para dashboard, APIs e relatórios.
"""


def build_safety_status(
    trading_enabled: bool = False,
    real_orders_enabled: bool = False,
    testnet_orders_enabled: bool = False,
    human_confirm_required: bool = True,
    environment: str = "BINANCE_FUTURES_TESTNET",
) -> dict:
    """
    Monta um status de segurança padronizado do robô.
    """

    blockers = []
    warnings = []
    status = "SEGURO_BLOQUEADO"

    if real_orders_enabled:
        status = "RISCO_CRITICO"
        blockers.append("Ordens reais aparecem como habilitadas. Real deve permanecer bloqueado.")

    if trading_enabled and not human_confirm_required:
        status = "RISCO_ALTO"
        blockers.append("Trading habilitado sem confirmação humana obrigatória.")

    if testnet_orders_enabled and not human_confirm_required:
        status = "RISCO_ALTO"
        blockers.append("Ordens Testnet habilitadas sem confirmação humana.")

    if not trading_enabled:
        blockers.append("Trading geral está bloqueado por segurança.")

    if not real_orders_enabled:
        blockers.append("Ordens reais estão bloqueadas.")

    if not testnet_orders_enabled:
        blockers.append("Ordens Testnet estão bloqueadas nesta fase.")

    if human_confirm_required:
        warnings.append("Confirmação humana obrigatória está ativa.")

    if environment != "BINANCE_FUTURES_TESTNET":
        warnings.append("Ambiente diferente de BINANCE_FUTURES_TESTNET. Validar antes de qualquer avanço.")

    return {
        "status": status,
        "environment": environment,
        "trading_enabled": trading_enabled,
        "real_orders_enabled": real_orders_enabled,
        "testnet_orders_enabled": testnet_orders_enabled,
        "human_confirm_required": human_confirm_required,
        "blockers": blockers,
        "warnings": warnings,
        "message": "Safety Status Engine ativo. Nenhuma ordem é executada por este módulo.",
    }