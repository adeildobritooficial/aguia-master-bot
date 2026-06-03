from __future__ import annotations

from dataclasses import dataclass, asdict
from decimal import Decimal, ROUND_DOWN
from typing import Dict, Any, Optional


@dataclass
class OrderPlan:
    ok: bool
    action: str
    environment: str
    symbol: str
    side: str
    order_type: str
    entry_price: float
    margin_usdt: float
    leverage: int
    notional_usdt: float
    quantity: float
    partial_take_profit_price: Optional[float]
    partial_close_percent: Optional[float]
    invalidation_price: Optional[float]
    reduce_only_for_entry: bool
    reduce_only_for_partial_exit: bool
    human_confirmation_required: bool
    trading_enabled: bool
    testnet_orders_enabled: bool
    safety_status: str
    message: str
    warnings: list


def _floor_decimal(value: Decimal, step: Decimal) -> Decimal:
    if step <= 0:
        return value
    return (value / step).to_integral_value(rounding=ROUND_DOWN) * step


def _to_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        if value is None:
            return Decimal(default)
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def build_order_plan(
    symbol: str,
    side: str,
    entry_price: float,
    margin_usdt: float,
    leverage: int,
    order_type: str = "LIMIT",
    environment: str = "BINANCE_FUTURES_TESTNET",
    partial_take_profit_price: Optional[float] = None,
    partial_close_percent: Optional[float] = None,
    invalidation_price: Optional[float] = None,
    quantity_step: str = "0.001",
    min_qty: str = "0.001",
    trading_enabled: bool = False,
    testnet_orders_enabled: bool = False,
    human_confirmation_required: bool = True,
) -> Dict[str, Any]:
    """
    Planejador seguro de ordem.

    IMPORTANTE:
    - Este arquivo NÃO executa ordem.
    - Este arquivo apenas calcula e prepara a proposta.
    - Por padrão, trading_enabled=False e testnet_orders_enabled=False.
    - Entrada nunca usa reduceOnly.
    - Saída parcial deve usar reduceOnly=True.
    """

    warnings = []

    symbol = str(symbol).upper().strip()
    side = str(side).upper().strip()
    order_type = str(order_type).upper().strip()
    environment = str(environment).upper().strip()

    entry = _to_decimal(entry_price)
    margin = _to_decimal(margin_usdt)
    lev = int(leverage)

    step = _to_decimal(quantity_step, "0.001")
    minimum_qty = _to_decimal(min_qty, "0.001")

    if not symbol:
        return asdict(OrderPlan(
            ok=False,
            action="BLOCK",
            environment=environment,
            symbol=symbol,
            side=side,
            order_type=order_type,
            entry_price=float(entry),
            margin_usdt=float(margin),
            leverage=lev,
            notional_usdt=0.0,
            quantity=0.0,
            partial_take_profit_price=partial_take_profit_price,
            partial_close_percent=partial_close_percent,
            invalidation_price=invalidation_price,
            reduce_only_for_entry=False,
            reduce_only_for_partial_exit=True,
            human_confirmation_required=human_confirmation_required,
            trading_enabled=trading_enabled,
            testnet_orders_enabled=testnet_orders_enabled,
            safety_status="BLOQUEADO",
            message="Símbolo inválido.",
            warnings=["Informe um ativo válido, exemplo: BTCUSDT."],
        ))

    if side not in ("BUY", "SELL", "LONG", "SHORT"):
        warnings.append("Direção inválida. Use LONG, SHORT, BUY ou SELL.")

    if side == "LONG":
        side = "BUY"
    elif side == "SHORT":
        side = "SELL"

    if entry <= 0:
        warnings.append("Preço de entrada precisa ser maior que zero.")

    if margin <= 0:
        warnings.append("Margem precisa ser maior que zero.")

    if lev <= 0:
        warnings.append("Alavancagem precisa ser maior que zero.")

    if lev > 20:
        warnings.append("Alavancagem acima de 20x exige cautela extra e deve ser bloqueada para iniciantes.")

    if margin > 50:
        warnings.append("Margem acima de 50 USDT exige revisão manual antes de qualquer teste.")

    if order_type not in ("LIMIT", "MARKET"):
        warnings.append("Tipo de ordem inválido. Use LIMIT ou MARKET.")

    notional = margin * Decimal(lev) if margin > 0 and lev > 0 else Decimal("0")
    raw_qty = notional / entry if entry > 0 else Decimal("0")
    qty = _floor_decimal(raw_qty, step)

    if qty < minimum_qty:
        warnings.append("Quantidade calculada ficou abaixo do mínimo operacional configurado.")

    if partial_close_percent is not None:
        pct = _to_decimal(partial_close_percent)
        if pct <= 0 or pct > 100:
            warnings.append("Percentual de saída parcial precisa estar entre 1 e 100.")
    else:
        pct = None

    if partial_take_profit_price is not None:
        tp = _to_decimal(partial_take_profit_price)
        if tp <= 0:
            warnings.append("Preço de alvo parcial precisa ser maior que zero.")

    if invalidation_price is not None:
        inv = _to_decimal(invalidation_price)
        if inv <= 0:
            warnings.append("Preço de invalidação precisa ser maior que zero.")

    # Regra central de segurança
    can_execute_now = (
        trading_enabled is True
        and testnet_orders_enabled is True
        and human_confirmation_required is False
        and len(warnings) == 0
    )

    if can_execute_now:
        action = "READY_FOR_TESTNET_EXECUTION"
        safety_status = "LIBERADO SOMENTE PARA TESTNET"
        message = "Plano tecnicamente válido para Testnet, desde que exista confirmação operacional externa."
        ok = True
    else:
        action = "PREPARE_ONLY"
        safety_status = "BLOQUEADO PARA EXECUÇÃO"
        message = (
            "Plano preparado em modo seguro. Nenhuma ordem deve ser executada automaticamente. "
            "Exige confirmação humana e validação final antes de qualquer teste."
        )
        ok = len(warnings) == 0

    plan = OrderPlan(
        ok=ok,
        action=action,
        environment=environment,
        symbol=symbol,
        side=side,
        order_type=order_type,
        entry_price=float(entry),
        margin_usdt=float(margin),
        leverage=lev,
        notional_usdt=float(notional),
        quantity=float(qty),
        partial_take_profit_price=partial_take_profit_price,
        partial_close_percent=partial_close_percent,
        invalidation_price=invalidation_price,
        reduce_only_for_entry=False,
        reduce_only_for_partial_exit=True,
        human_confirmation_required=human_confirmation_required,
        trading_enabled=trading_enabled,
        testnet_orders_enabled=testnet_orders_enabled,
        safety_status=safety_status,
        message=message,
        warnings=warnings,
    )

    return asdict(plan)


def simulate_eth_example() -> Dict[str, Any]:
    return build_order_plan(
        symbol="ETHUSDT",
        side="LONG",
        order_type="LIMIT",
        entry_price=3000,
        margin_usdt=25,
        leverage=20,
        partial_take_profit_price=3060,
        partial_close_percent=50,
        invalidation_price=2900,
        trading_enabled=False,
        testnet_orders_enabled=False,
        human_confirmation_required=True,
    )


if __name__ == "__main__":
    import json

    result = simulate_eth_example()
    print(json.dumps(result, indent=2, ensure_ascii=False))