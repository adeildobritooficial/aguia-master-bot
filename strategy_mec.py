# strategy_mec.py

def evaluate_entry(symbol: str, market_data: dict, btc_context: dict | None = None) -> dict:
    """
    Avalia uma possível entrada com base em uma versão inicial das regras do Método Águia Cripto.

    Esta função ainda é simplificada:
    - não executa ordens;
    - não usa IA;
    - não usa API privada;
    - apenas classifica o cenário.
    """

    last_4h = market_data["last_4h_candle"]
    last_5m = market_data["last_5m_candle"]
    volume_5m = market_data["volume_5m"]
    sr = market_data["support_resistance_4h"]

    near_support = market_data["near_support"]
    near_resistance = market_data["near_resistance"]

    btc_blocking_long = False
    btc_blocking_short = False

    if btc_context:
        btc_5m = btc_context["last_5m_candle"]
        btc_volume = btc_context["volume_5m"]

        # Se BTC está caindo forte com volume alto, bloqueia Long em altcoins
        if btc_5m["direction"] == "RED" and btc_volume["status"] == "HIGH":
            btc_blocking_long = True

        # Se BTC está subindo forte com volume alto, bloqueia Short em altcoins
        if btc_5m["direction"] == "GREEN" and btc_volume["status"] == "HIGH":
            btc_blocking_short = True

    decision = "AGUARDAR"
    direction = "NONE"
    confidence = "BAIXA"
    reasons = []
    warnings = []

    # Cenário de possível Long
    if near_support and last_5m["direction"] == "GREEN" and volume_5m["status"] in ["NORMAL", "HIGH"]:
        if btc_blocking_long:
            decision = "REJEITAR"
            direction = "LONG"
            confidence = "BAIXA"
            reasons.append("Long rejeitado porque o BTC está contra com candle vermelho e volume alto.")
        else:
            decision = "POSSÍVEL LONG"
            direction = "LONG"
            confidence = "MÉDIA"
            reasons.append("Preço próximo de suporte no 4H.")
            reasons.append("Último candle de 5M está verde.")
            reasons.append("Volume no 5M está normal ou alto.")
            warnings.append("Aguardar reteste ou pullback curto antes de entrada disciplinada.")

    # Cenário de possível Short
    elif near_resistance and last_5m["direction"] == "RED" and volume_5m["status"] in ["NORMAL", "HIGH"]:
        if btc_blocking_short:
            decision = "REJEITAR"
            direction = "SHORT"
            confidence = "BAIXA"
            reasons.append("Short rejeitado porque o BTC está contra com candle verde e volume alto.")
        else:
            decision = "POSSÍVEL SHORT"
            direction = "SHORT"
            confidence = "MÉDIA"
            reasons.append("Preço próximo de resistência no 4H.")
            reasons.append("Último candle de 5M está vermelho.")
            reasons.append("Volume no 5M está normal ou alto.")
            warnings.append("Aguardar rejeição clara ou reteste antes de entrada disciplinada.")

    # Evitar meio do canal
    else:
        decision = "AGUARDAR"
        direction = "NONE"
        confidence = "BAIXA"
        reasons.append("Cenário ainda sem confluência suficiente.")
        reasons.append("Preço pode estar longe de suporte/resistência ou sem candle favorável.")
        warnings.append("Não operar no meio do canal ou sem confirmação.")

    return {
        "symbol": symbol,
        "decision": decision,
        "direction": direction,
        "confidence": confidence,
        "current_price": sr["current_price"],
        "support": sr["support"],
        "resistance": sr["resistance"],
        "distance_to_support_percent": sr["distance_to_support_percent"],
        "distance_to_resistance_percent": sr["distance_to_resistance_percent"],
        "reasons": reasons,
        "warnings": warnings,
    }


def evaluate_3x_scenario(position_side: str, market_data: dict, candles_4h_against: int) -> dict:
    """
    Avalia se existe início de cenário para 3X.

    Nesta versão, o robô apenas alerta.
    Ele NÃO faz 3X automaticamente.
    """

    last_5m = market_data["last_5m_candle"]
    volume_5m = market_data["volume_5m"]

    status = "3X BLOQUEADO"
    reasons = []
    warnings = []

    if candles_4h_against < 8:
        reasons.append("Ainda não houve contagem mínima de 8 candles no 4H.")
        warnings.append("Não fazer 3X cedo demais.")
    elif candles_4h_against > 15:
        reasons.append("Contagem passou de 15 candles no 4H; cenário pode estar atrasado.")
        warnings.append("Reavaliar estrutura antes de qualquer defesa.")
    else:
        if position_side.upper() == "LONG":
            if last_5m["direction"] == "GREEN" and volume_5m["status"] in ["NORMAL", "HIGH"]:
                status = "ALERTA 3X LONG"
                reasons.append("Contagem de candles no 4H está dentro da janela.")
                reasons.append("5M mostrou candle verde favorável.")
                reasons.append("Volume está normal ou alto.")
                warnings.append("Confirmar lateralização, risco da banca e liquidação antes de qualquer 3X.")
            else:
                reasons.append("Ainda não há candle verde favorável no 5M para defesa de Long.")

        elif position_side.upper() == "SHORT":
            if last_5m["direction"] == "RED" and volume_5m["status"] in ["NORMAL", "HIGH"]:
                status = "ALERTA 3X SHORT"
                reasons.append("Contagem de candles no 4H está dentro da janela.")
                reasons.append("5M mostrou candle vermelho favorável.")
                reasons.append("Volume está normal ou alto.")
                warnings.append("Confirmar lateralização, risco da banca e liquidação antes de qualquer 3X.")
            else:
                reasons.append("Ainda não há candle vermelho favorável no 5M para defesa de Short.")
        else:
            reasons.append("Direção da posição inválida para análise de 3X.")

    return {
        "status": status,
        "candles_4h_against": candles_4h_against,
        "reasons": reasons,
        "warnings": warnings,
        "reduce_only_rule": "Após 3X, qualquer saída parcial ou total deve usar Reduce Only.",
    }