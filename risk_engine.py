# risk_engine.py

from config import (
    MAX_RISK_PERCENT,
    BLOCK_RISK_PERCENT,
    KILL_SWITCH_RISK_PERCENT,
)


def evaluate_account_risk(
    balance_usdt: float,
    current_risk_percent: float,
    open_positions: int,
    planned_margin_usdt: float,
    leverage: int,
    liquidation_price: float | None = None,
    invalidation_price: float | None = None,
    direction: str | None = None,
) -> dict:
    """
    Avalia risco da operação antes de qualquer execução.

    Esta primeira versão é educacional e conservadora.
    Não executa ordens.
    """

    status = "PERMITIR_COM_CAUTELA"
    reasons = []
    warnings = []

    margin_percent = (planned_margin_usdt / balance_usdt) * 100 if balance_usdt > 0 else 0
    notional_exposure = planned_margin_usdt * leverage

    # Risco crítico
    if current_risk_percent >= KILL_SWITCH_RISK_PERCENT:
        status = "KILL_SWITCH"
        reasons.append("Risco da banca acima ou igual a 15%. Bloqueio total e proteção.")
    elif current_risk_percent >= BLOCK_RISK_PERCENT:
        status = "BLOQUEAR"
        reasons.append("Risco da banca acima ou igual a 10%. Bloquear novas entradas.")
    elif current_risk_percent > MAX_RISK_PERCENT:
        status = "PROTEGER"
        reasons.append("Risco da banca acima da zona ideal. Prioridade é proteção.")
    else:
        reasons.append("Risco atual dentro da zona aceitável.")

    # Número de operações abertas
    if open_positions >= 5:
        status = "BLOQUEAR" if status not in ["KILL_SWITCH"] else status
        reasons.append("Número de operações abertas elevado. Bloquear nova entrada.")
    elif open_positions == 4:
        warnings.append("Com 4 operações abertas, margem deve ser extremamente controlada.")
    elif open_positions == 3:
        warnings.append("Ao abrir nova posição, passará para 4 operações. Não aumentar a mão.")

    # Margem por operação
    if open_positions >= 3 and margin_percent > 2.5:
        status = "BLOQUEAR" if status not in ["KILL_SWITCH"] else status
        reasons.append("Margem acima de 2,5% com 3 ou mais operações abertas.")
    elif margin_percent > 5:
        status = "BLOQUEAR" if status not in ["KILL_SWITCH"] else status
        reasons.append("Margem acima de 5% da banca. Bloquear.")
    else:
        reasons.append(f"Margem planejada representa {margin_percent:.2f}% da banca.")

    # Alavancagem
    if leverage > 50:
        status = "BLOQUEAR" if status not in ["KILL_SWITCH"] else status
        reasons.append("Alavancagem acima de 50X bloqueada.")
    elif leverage > 20:
        warnings.append("Alavancagem acima de 20X exige experiência e validação extra.")
    else:
        reasons.append("Alavancagem dentro do limite inicial/prudente.")

    # Liquidação vs invalidação
    if liquidation_price and invalidation_price and direction:
        direction_upper = direction.upper()

        if direction_upper == "LONG":
            if liquidation_price >= invalidation_price:
                status = "BLOQUEAR" if status not in ["KILL_SWITCH"] else status
                reasons.append("Para Long, liquidação está acima ou igual à invalidação. Perigoso.")
            else:
                reasons.append("Para Long, liquidação está abaixo da invalidação. Estruturalmente correto.")

        elif direction_upper == "SHORT":
            if liquidation_price <= invalidation_price:
                status = "BLOQUEAR" if status not in ["KILL_SWITCH"] else status
                reasons.append("Para Short, liquidação está abaixo ou igual à invalidação. Perigoso.")
            else:
                reasons.append("Para Short, liquidação está acima da invalidação. Estruturalmente correto.")

    return {
        "status": status,
        "balance_usdt": balance_usdt,
        "current_risk_percent": current_risk_percent,
        "open_positions": open_positions,
        "planned_margin_usdt": planned_margin_usdt,
        "margin_percent": round(margin_percent, 2),
        "leverage": leverage,
        "notional_exposure": round(notional_exposure, 2),
        "reasons": reasons,
        "warnings": warnings,
    }