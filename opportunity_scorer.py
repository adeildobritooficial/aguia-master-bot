# opportunity_scorer.py


def score_opportunity(item: dict, btc_context: dict | None = None) -> dict:
    """
    Pontua uma oportunidade com base em confluências técnicas.

    Objetivo:
    - Evitar score alto fácil.
    - Bloquear oportunidades sem direção.
    - Valorizar região clara, candle favorável, volume e BTC alinhado.
    - Penalizar meio do canal, baixa confirmação e BTC contra.
    """

    score = 0
    positives = []
    negatives = []
    hard_blocks = []

    decision = item.get("decision", "AGUARDAR")
    direction = item.get("direction", "NONE")
    confidence = item.get("confidence", "BAIXA")

    candle_4h = item.get("candle_4h")
    candle_5m = item.get("candle_5m")
    volume_5m = item.get("volume_5m")

    distance_to_support = item.get("distance_to_support_percent")
    distance_to_resistance = item.get("distance_to_resistance_percent")

    # ============================================================
    # 1. Decisão original do robô
    # ============================================================

    if decision == "POSSÍVEL LONG":
        score += 25
        positives.append("Estrutura inicial favorece possível Long.")

    elif decision == "POSSÍVEL SHORT":
        score += 25
        positives.append("Estrutura inicial favorece possível Short.")

    elif decision == "AGUARDAR":
        score += 0
        negatives.append("Robô ainda classificou o ativo como AGUARDAR.")
        hard_blocks.append("Sem decisão operacional confirmada.")

    elif decision == "ERRO":
        score -= 50
        negatives.append("Erro na análise do ativo.")
        hard_blocks.append("Ativo com erro técnico no ciclo.")

    else:
        score -= 10
        negatives.append("Decisão não reconhecida ou sem setup claro.")
        hard_blocks.append("Decisão original não confirma entrada.")

    # ============================================================
    # 2. Direção operacional
    # ============================================================

    if direction == "LONG":
        score += 10
        positives.append("Direção compradora identificada.")

    elif direction == "SHORT":
        score += 10
        positives.append("Direção vendedora identificada.")

    else:
        score -= 25
        negatives.append("Sem direção operacional definida.")
        hard_blocks.append("Direção NONE impede oportunidade forte.")

    # ============================================================
    # 3. Região técnica — suporte e resistência
    # ============================================================

    near_support = False
    near_resistance = False
    has_room_to_target = False
    possible_middle_channel = False

    if distance_to_support is not None:
        if distance_to_support <= 2:
            near_support = True
            score += 18
            positives.append("Preço próximo do suporte no 4H.")
        elif distance_to_support <= 4:
            score += 8
            positives.append("Preço relativamente próximo do suporte.")
        else:
            score -= 8
            negatives.append("Preço distante do suporte.")

    if distance_to_resistance is not None:
        if distance_to_resistance <= 2:
            near_resistance = True

        if direction == "LONG":
            if distance_to_resistance >= 3:
                has_room_to_target = True
                score += 12
                positives.append("Existe espaço técnico até a resistência para Long.")
            else:
                score -= 15
                negatives.append("Pouco espaço até a resistência para Long.")
                hard_blocks.append("Alvo curto demais para Long.")

        elif direction == "SHORT":
            if distance_to_support is not None and distance_to_support >= 3:
                has_room_to_target = True
                score += 12
                positives.append("Existe espaço técnico até o suporte para Short.")
            else:
                score -= 15
                negatives.append("Pouco espaço até o suporte para Short.")
                hard_blocks.append("Alvo curto demais para Short.")

    if (
        distance_to_support is not None
        and distance_to_resistance is not None
        and distance_to_support > 2
        and distance_to_resistance > 2
        and direction == "NONE"
    ):
        possible_middle_channel = True
        score -= 25
        negatives.append("Ativo possivelmente no meio do canal.")
        hard_blocks.append("Meio do canal sem região clara.")

    # ============================================================
    # 4. Candle 5M — gatilho de entrada
    # ============================================================

    candle_5m_favorable = False

    if direction == "LONG":
        if candle_5m == "GREEN":
            candle_5m_favorable = True
            score += 15
            positives.append("Candle 5M favorável para Long.")
        elif candle_5m == "RED":
            score -= 20
            negatives.append("Candle 5M contra possível Long.")
            hard_blocks.append("Candle 5M contra a entrada Long.")

    elif direction == "SHORT":
        if candle_5m == "RED":
            candle_5m_favorable = True
            score += 15
            positives.append("Candle 5M favorável para Short.")
        elif candle_5m == "GREEN":
            score -= 20
            negatives.append("Candle 5M contra possível Short.")
            hard_blocks.append("Candle 5M contra a entrada Short.")

    else:
        score -= 5
        negatives.append("Sem direção, candle 5M não pode validar entrada.")

    # ============================================================
    # 5. Candle 4H — contexto
    # ============================================================

    if direction == "LONG":
        if candle_4h == "GREEN":
            score += 8
            positives.append("Candle 4H verde favorece leitura compradora.")
        elif candle_4h == "RED":
            score -= 8
            negatives.append("Candle 4H vermelho pesa contra Long.")

    elif direction == "SHORT":
        if candle_4h == "RED":
            score += 8
            positives.append("Candle 4H vermelho favorece leitura vendedora.")
        elif candle_4h == "GREEN":
            score -= 8
            negatives.append("Candle 4H verde pesa contra Short.")

    # ============================================================
    # 6. Volume
    # ============================================================

    volume_confirmed = False

    if volume_5m == "HIGH":
        volume_confirmed = True
        score += 15
        positives.append("Volume 5M alto, indicando participação do mercado.")

    elif volume_5m == "NORMAL":
        volume_confirmed = True
        score += 8
        positives.append("Volume 5M normal, sem bloqueio por fraqueza.")

    elif volume_5m == "LOW":
        score -= 18
        negatives.append("Volume 5M baixo, sem confirmação suficiente.")
        hard_blocks.append("Volume baixo bloqueia oportunidade forte.")

    else:
        score -= 10
        negatives.append("Volume 5M indefinido ou inválido.")
        hard_blocks.append("Volume não confirmado.")

    # ============================================================
    # 7. Confiança
    # ============================================================

    confidence_ok = False

    if confidence == "ALTA":
        confidence_ok = True
        score += 12
        positives.append("Confiança alta na leitura.")

    elif confidence == "MÉDIA":
        confidence_ok = True
        score += 8
        positives.append("Confiança média na leitura.")

    elif confidence == "BAIXA":
        score -= 12
        negatives.append("Confiança baixa na leitura.")
        hard_blocks.append("Confiança baixa impede oportunidade forte.")

    # ============================================================
    # 8. Filtro BTC
    # ============================================================

    btc_aligned_or_neutral = True

    if btc_context:
        btc_candle_5m = btc_context.get("candle_5m")
        btc_volume_5m = btc_context.get("volume_5m")

        if direction == "LONG":
            if btc_candle_5m == "RED" and btc_volume_5m in ["HIGH", "NORMAL"]:
                btc_aligned_or_neutral = False
                score -= 25
                negatives.append("BTC está contra Long no 5M.")
                hard_blocks.append("BTC contra bloqueia oportunidade forte para Long.")
            elif btc_candle_5m == "GREEN":
                score += 8
                positives.append("BTC não está contra Long.")

        elif direction == "SHORT":
            if btc_candle_5m == "GREEN" and btc_volume_5m in ["HIGH", "NORMAL"]:
                btc_aligned_or_neutral = False
                score -= 25
                negatives.append("BTC está contra Short no 5M.")
                hard_blocks.append("BTC contra bloqueia oportunidade forte para Short.")
            elif btc_candle_5m == "RED":
                score += 8
                positives.append("BTC não está contra Short.")

    # ============================================================
    # 9. Travas de segurança do score
    # ============================================================

    # Se não há direção, nunca pode passar de 35
    if direction == "NONE":
        score = min(score, 35)

    # Se a decisão original é AGUARDAR, nunca pode passar de 45
    if decision == "AGUARDAR":
        score = min(score, 45)

    # Se volume é baixo, nunca pode passar de 55
    if volume_5m == "LOW":
        score = min(score, 55)

    # Se candle 5M está contra, nunca pode passar de 55
    if direction in ["LONG", "SHORT"] and not candle_5m_favorable:
        score = min(score, 55)

    # Se BTC está contra, nunca pode passar de 50
    if not btc_aligned_or_neutral:
        score = min(score, 50)

    # Se não há espaço até alvo, nunca pode passar de 60
    if direction in ["LONG", "SHORT"] and not has_room_to_target:
        score = min(score, 60)

    # Se está no meio do canal sem direção, trava mais forte
    if possible_middle_channel:
        score = min(score, 30)

    # Garantir score entre 0 e 100
    score = max(0, min(100, score))

    # ============================================================
    # 10. Classificação final mais rigorosa
    # ============================================================

    can_be_strong = (
        decision in ["POSSÍVEL LONG", "POSSÍVEL SHORT"]
        and direction in ["LONG", "SHORT"]
        and candle_5m_favorable
        and volume_confirmed
        and btc_aligned_or_neutral
        and confidence_ok
        and has_room_to_target
    )

    if score >= 80 and can_be_strong:
        classification = "OPORTUNIDADE FORTE"
    elif score >= 60 and direction in ["LONG", "SHORT"]:
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
        "hard_blocks": hard_blocks,
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
                "hard_blocks": scored["hard_blocks"],
            }
        )

    ranked = sorted(
        ranked,
        key=lambda x: x["score"],
        reverse=True,
    )

    return ranked