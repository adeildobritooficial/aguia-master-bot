# opportunity_scorer.py

def score_opportunity(item: dict, btc_context: dict | None = None) -> dict:
    """
    Pontua uma oportunidade com base em confluências técnicas.

    Ideia central:
    - Não operar no meio do canal.
    - Valorizar suporte/resistência.
    - Valorizar candle 5M favorável.
    - Valorizar volume.
    - Penalizar BTC contra.
    - Penalizar baixa confluência.
    """

    score = 0
    positives = []
    negatives = []

    decision = item.get("decision", "AGUARDAR")
    direction = item.get("direction", "NONE")
    confidence = item.get("confidence", "BAIXA")

    candle_4h = item.get("candle_4h")
    candle_5m = item.get("candle_5m")
    volume_5m = item.get("volume_5m")

    distance_to_support = item.get("distance_to_support_percent")
    distance_to_resistance = item.get("distance_to_resistance_percent")

    # ============================================================
    # Pontos por decisão original
    # ============================================================

    if decision == "POSSÍVEL LONG":
        score += 25
        positives.append("Estrutura inicial favorece possível Long.")

    elif decision == "POSSÍVEL SHORT":
        score += 25
        positives.append("Estrutura inicial favorece possível Short.")

    elif decision == "AGUARDAR":
        score += 5
        negatives.append("Robô ainda classificou o ativo como aguardar.")

    elif decision == "ERRO":
        score -= 50
        negatives.append("Erro na análise do ativo.")

    # ============================================================
    # Pontos por região técnica
    # ============================================================

    if distance_to_support is not None:
        if distance_to_support <= 2:
            score += 20
            positives.append("Preço próximo do suporte no 4H.")
        elif distance_to_support <= 4:
            score += 10
            positives.append("Preço relativamente próximo do suporte.")
        else:
            score -= 10
            negatives.append("Preço distante do suporte.")

    if distance_to_resistance is not None:
        if direction == "LONG":
            if distance_to_resistance >= 3:
                score += 10
                positives.append("Existe espaço razoável até a resistência.")
            else:
                score -= 10
                negatives.append("Pouco espaço até a resistência para Long.")

        elif direction == "SHORT":
            if distance_to_support >= 3:
                score += 10
                positives.append("Existe espaço razoável até o suporte para Short.")
            else:
                score -= 10
                negatives.append("Pouco espaço até o suporte para Short.")

    # ============================================================
    # Candle 5M
    # ============================================================

    if direction == "LONG":
        if candle_5m == "GREEN":
            score += 15
            positives.append("Candle 5M favorável para Long.")
        elif candle_5m == "RED":
            score -= 15
            negatives.append("Candle 5M contra possível Long.")

    elif direction == "SHORT":
        if candle_5m == "RED":
            score += 15
            positives.append("Candle 5M favorável para Short.")
        elif candle_5m == "GREEN":
            score -= 15
            negatives.append("Candle 5M contra possível Short.")

    else:
        if candle_5m in ["GREEN", "RED"]:
            score += 2
        else:
            negatives.append("Candle 5M sem direção clara.")

    # ============================================================
    # Candle 4H
    # ============================================================

    if direction == "LONG" and candle_4h == "GREEN":
        score += 8
        positives.append("Candle 4H verde favorece leitura compradora.")

    elif direction == "SHORT" and candle_4h == "RED":
        score += 8
        positives.append("Candle 4H vermelho favorece leitura vendedora.")

    # ============================================================
    # Volume
    # ============================================================

    if volume_5m == "HIGH":
        score += 15
        positives.append("Volume 5M alto, indicando participação do mercado.")

    elif volume_5m == "NORMAL":
        score += 8
        positives.append("Volume 5M normal, sem bloqueio por fraqueza.")

    elif volume_5m == "LOW":
        score -= 12
        negatives.append("Volume 5M baixo, falta confirmação.")

    # ============================================================
    # Confiança
    # ============================================================

    if confidence == "ALTA":
        score += 15
        positives.append("Confiança alta na leitura.")

    elif confidence == "MÉDIA":
        score += 10
        positives.append("Confiança média na leitura.")

    elif confidence == "BAIXA":
        score -= 5
        negatives.append("Confiança baixa na leitura.")

    # ============================================================
    # Filtro BTC
    # ============================================================

    if btc_context:
        btc_candle_5m = btc_context.get("candle_5m")
        btc_volume_5m = btc_context.get("volume_5m")

        if direction == "LONG":
            if btc_candle_5m == "RED" and btc_volume_5m == "HIGH":
                score -= 25
                negatives.append("BTC está contra Long com candle vermelho e volume alto.")
            elif btc_candle_5m == "GREEN":
                score += 10
                positives.append("BTC não está contra Long.")

        elif direction == "SHORT":
            if btc_candle_5m == "GREEN" and btc_volume_5m == "HIGH":
                score -= 25
                negatives.append("BTC está contra Short com candle verde e volume alto.")
            elif btc_candle_5m == "RED":
                score += 10
                positives.append("BTC não está contra Short.")

    # ============================================================
    # Penalidade por meio do canal
    # ============================================================

    if (
        distance_to_support is not None
        and distance_to_resistance is not None
        and distance_to_support > 2
        and distance_to_resistance > 2
        and direction == "NONE"
    ):
        score -= 20
        negatives.append("Ativo possivelmente no meio do canal, sem região clara.")

    # Garantir score entre 0 e 100
    score = max(0, min(100, score))

    # ============================================================
    # Classificação final
    # ============================================================

    if score >= 80:
        classification = "OPORTUNIDADE FORTE"
    elif score >= 60:
        classification = "POSSÍVEL OPERAÇÃO"
    elif score >= 40:
        classification = "AGUARDAR CONFIRMAÇÃO"
    else:
        classification = "REJEITAR / SEM SETUP"

    return {
        "score": score,
        "classification": classification,
        "positives": positives,
        "negatives": negatives,
    }


def rank_opportunities(summary: list[dict], btc_context: dict | None = None) -> list[dict]:
    """
    Recebe a lista de ativos analisados e devolve ranking ordenado por score.
    """

    ranked = []

    for item in summary:
        scored = score_opportunity(item, btc_context=btc_context)

        ranked.append(
            {
                "symbol": item.get("symbol"),
                "price": item.get("price"),
                "decision": item.get("decision"),
                "direction": item.get("direction"),
                "confidence": item.get("confidence"),
                "score": scored["score"],
                "classification": scored["classification"],
                "positives": scored["positives"],
                "negatives": scored["negatives"],
            }
        )

    ranked = sorted(
        ranked,
        key=lambda x: x["score"],
        reverse=True,
    )

    return ranked