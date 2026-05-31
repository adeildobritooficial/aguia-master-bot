# app.py

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime

from main import run_observer

app = FastAPI(
    title="ÁGUIA MASTER BOT",
    description="Robô observador do Método Águia Cripto em modo seguro.",
    version="1.4.0",
)


@app.get("/")
def home():
    return {
        "name": "ÁGUIA MASTER BOT",
        "status": "online",
        "mode": "observer",
        "message": "Robô online. Nenhuma ordem é executada nesta fase.",
        "routes": {
            "status": "/status",
            "run_json": "/run-json",
            "dashboard": "/dashboard",
        },
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/status")
def status():
    return {
        "status": "online",
        "mode": "OBSERVER",
        "environment": "BINANCE FUTURES TESTNET / PUBLIC DATA",
        "orders_enabled": False,
        "api_keys_required": False,
        "safety": "Nenhuma ordem real ou testnet é executada nesta fase.",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/run")
def run_bot():
    return run_observer()


@app.get("/run-json")
def run_json():
    return run_observer()


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    report = run_observer()

    if report.get("status") != "success":
        return f"""
        <html>
            <head>
                <title>ÁGUIA MASTER BOT</title>
                <meta charset="utf-8">
            </head>
            <body style="font-family: Arial; background:#111827; color:white; padding:30px;">
                <h1>ÁGUIA MASTER BOT</h1>
                <h2 style="color:#ff5555;">Erro no ciclo</h2>
                <p>{report.get("message", "Erro desconhecido")}</p>
                <pre>{report}</pre>
            </body>
        </html>
        """

    def badge_color(text: str) -> str:
        if "OPORTUNIDADE FORTE" in text:
            return "#16a34a"
        if "POSSÍVEL OPERAÇÃO" in text:
            return "#22c55e"
        if "LONG" in text:
            return "#16a34a"
        if "SHORT" in text:
            return "#dc2626"
        if "AGUARDAR" in text or "CONFIRMAÇÃO" in text:
            return "#f59e0b"
        if "REJEITAR" in text or "SEM SETUP" in text or "NÃO OPERAR" in text:
            return "#dc2626"
        return "#6b7280"

    btc = report["btc_context"]
    selection = report["symbol_selection"]
    cycle = report["cycle_summary"]
    risk = report["risk"]
    x3 = report["x3"]

    top_opportunities = report.get("top_opportunities", [])
    best = top_opportunities[0] if top_opportunities else None

    if not best:
        general_status = "AGUARDAR"
        general_color = "#f59e0b"
        general_reason = "Nenhum ativo foi ranqueado neste ciclo."
        general_action = "Não operar agora. Aguardar nova leitura do mercado."

    elif best["classification"] == "OPORTUNIDADE FORTE":
        general_status = "OPORTUNIDADE FORTE"
        general_color = "#16a34a"
        general_reason = f"Melhor ativo do ciclo: {best['symbol']} com score {best['score']}/100."
        general_action = "Analisar manualmente antes de qualquer execução. Ainda não executar ordem automática."

    elif best["classification"] == "POSSÍVEL OPERAÇÃO":
        general_status = "POSSÍVEL OPERAÇÃO"
        general_color = "#22c55e"
        general_reason = f"Existe possível setup em {best['symbol']}, mas ainda exige confirmação fina."
        general_action = "Aguardar confirmação de candle, volume, BTC e região antes de qualquer entrada."

    elif best["classification"] == "AGUARDAR CONFIRMAÇÃO":
        general_status = "AGUARDAR CONFIRMAÇÃO"
        general_color = "#f59e0b"
        general_reason = f"Melhor ativo atual: {best['symbol']}, mas sem confluência suficiente."
        general_action = "Não entrar agora. Aguardar novo ciclo com confirmação técnica."

    else:
        general_status = "NÃO OPERAR"
        general_color = "#dc2626"
        general_reason = "Nenhuma oportunidade operacional forte encontrada neste ciclo."
        general_action = "Preservar capital. Não operar no meio do canal, sem direção ou sem volume."

    ranking_html = ""

    for index, item in enumerate(top_opportunities, start=1):
        color = badge_color(item["classification"])

        positives = "".join([f"<li>{p}</li>" for p in item.get("positives", [])[:4]])
        negatives = "".join([f"<li>{n}</li>" for n in item.get("negatives", [])[:4]])
        hard_blocks = "".join([f"<li>{b}</li>" for b in item.get("hard_blocks", [])[:4]])

        ranking_html += f"""
        <div style="background:#1f2937; border-radius:16px; padding:18px; margin-bottom:14px;">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
                <h3 style="margin:0;">#{index} {item["symbol"]}</h3>
                <span style="background:{color}; color:white; padding:7px 12px; border-radius:999px; font-weight:bold;">
                    {item["classification"]}
                </span>
            </div>

            <p>Score técnico: <strong>{item["score"]}/100</strong></p>
            <p>
                Decisão: <strong>{item["decision"]}</strong> |
                Direção: <strong>{item["direction"]}</strong> |
                Confiança: <strong>{item["confidence"]}</strong>
            </p>

            <h4 style="color:#93c5fd;">Pontos positivos</h4>
            <ul>{positives if positives else "<li>Nenhum ponto positivo relevante neste ciclo.</li>"}</ul>

            <h4 style="color:#fca5a5;">Pontos de atenção</h4>
            <ul>{negatives if negatives else "<li>Nenhum alerta relevante registrado.</li>"}</ul>

            <h4 style="color:#fcd34d;">Travas de segurança</h4>
            <ul>{hard_blocks if hard_blocks else "<li>Nenhuma trava crítica registrada.</li>"}</ul>
        </div>
        """

    cards_html = ""

    for item in report["summary"]:
        decision = item["decision"]
        color = badge_color(decision)

        reasons = "".join([f"<li>{reason}</li>" for reason in item.get("reasons", [])])
        warnings = "".join([f"<li>{warning}</li>" for warning in item.get("warnings", [])])

        ranking_item = next(
            (r for r in report["ranking"] if r["symbol"] == item["symbol"]),
            None,
        )

        score_html = ""

        if ranking_item:
            score_html = f"""
            <div style="background:#111827; padding:12px; border-radius:10px;">
                Score: <strong>{ranking_item["score"]}/100</strong>
            </div>
            <div style="background:#111827; padding:12px; border-radius:10px;">
                Classe: <strong>{ranking_item["classification"]}</strong>
            </div>
            """

        cards_html += f"""
        <div style="background:#1f2937; border-radius:16px; padding:22px; margin-bottom:20px; box-shadow:0 8px 20px rgba(0,0,0,0.25);">
            <div style="display:flex; justify-content:space-between; align-items:center; gap:15px;">
                <h2 style="margin:0; color:white;">{item["symbol"]}</h2>
                <span style="background:{color}; color:white; padding:8px 14px; border-radius:999px; font-weight:bold;">
                    {item["decision"]}
                </span>
            </div>

            <p style="font-size:18px; color:#d1d5db;">
                Preço: <strong>{item["price"]}</strong>
            </p>

            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px; margin-top:15px;">
                {score_html}
                <div style="background:#111827; padding:12px; border-radius:10px;">Direção: <strong>{item["direction"]}</strong></div>
                <div style="background:#111827; padding:12px; border-radius:10px;">Confiança: <strong>{item["confidence"]}</strong></div>
                <div style="background:#111827; padding:12px; border-radius:10px;">Candle 4H: <strong>{item["candle_4h"]}</strong></div>
                <div style="background:#111827; padding:12px; border-radius:10px;">Candle 5M: <strong>{item["candle_5m"]}</strong></div>
                <div style="background:#111827; padding:12px; border-radius:10px;">Volume 5M: <strong>{item["volume_5m"]}</strong></div>
                <div style="background:#111827; padding:12px; border-radius:10px;">Suporte 4H: <strong>{item["support_4h"]}</strong></div>
                <div style="background:#111827; padding:12px; border-radius:10px;">Resistência 4H: <strong>{item["resistance_4h"]}</strong></div>
                <div style="background:#111827; padding:12px; border-radius:10px;">Dist. Suporte: <strong>{item["distance_to_support_percent"]}%</strong></div>
                <div style="background:#111827; padding:12px; border-radius:10px;">Dist. Resistência: <strong>{item["distance_to_resistance_percent"]}%</strong></div>
            </div>

            <h3 style="color:#93c5fd;">Motivos</h3>
            <ul>{reasons if reasons else "<li>Sem motivos registrados.</li>"}</ul>

            <h3 style="color:#fcd34d;">Alertas</h3>
            <ul>{warnings if warnings else "<li>Sem alertas registrados.</li>"}</ul>
        </div>
        """

    html = f"""
    <html>
        <head>
            <title>ÁGUIA MASTER BOT</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>

        <body style="font-family: Arial, sans-serif; background:#0f172a; color:white; margin:0; padding:0;">
            <div style="max-width:1100px; margin:auto; padding:30px;">
                <header style="margin-bottom:30px;">
                    <h1 style="font-size:34px; margin-bottom:5px;">🦅 ÁGUIA MASTER BOT</h1>
                    <p style="color:#cbd5e1; font-size:17px;">
                        Robô observador do Método Águia Cripto — modo seguro, sem execução de ordens.
                    </p>
                    <p style="color:#94a3b8;">
                        Última atualização: {report["timestamp"]}
                    </p>
                </header>

                <div style="background:#1e293b; border-radius:16px; padding:22px; margin-bottom:25px;">
                    <h2>Resumo do Ciclo</h2>
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px;">
                        <div style="background:#111827; padding:12px; border-radius:10px;">Modo seleção: <strong>{selection["selection_mode"]}</strong></div>
                        <div style="background:#111827; padding:12px; border-radius:10px;">Lista branca: <strong>{selection["whitelist_enabled"]}</strong></div>
                        <div style="background:#111827; padding:12px; border-radius:10px;">Ativos analisados: <strong>{selection["symbols_count"]}</strong></div>
                        <div style="background:#111827; padding:12px; border-radius:10px;">Possíveis Longs: <strong>{cycle["possible_longs"]}</strong></div>
                        <div style="background:#111827; padding:12px; border-radius:10px;">Possíveis Shorts: <strong>{cycle["possible_shorts"]}</strong></div>
                        <div style="background:#111827; padding:12px; border-radius:10px;">Aguardando: <strong>{cycle["waiting"]}</strong></div>
                    </div>
                </div>

                <div style="background:#1e293b; border-radius:16px; padding:22px; margin-bottom:25px; border-left:6px solid {general_color};">
                    <h2>Decisão Geral do Ciclo</h2>

                    <div style="display:flex; flex-wrap:wrap; gap:12px; align-items:center; margin-bottom:15px;">
                        <span style="background:{general_color}; color:white; padding:10px 16px; border-radius:999px; font-weight:bold; font-size:18px;">
                            {general_status}
                        </span>
                    </div>

                    <p style="font-size:18px; color:#e5e7eb;">
                        <strong>Motivo:</strong> {general_reason}
                    </p>

                    <p style="font-size:18px; color:#fcd34d;">
                        <strong>Ação recomendada:</strong> {general_action}
                    </p>

                    <p style="color:#94a3b8;">
                        Regra de segurança: este robô ainda está em modo observador. Nenhuma ordem real ou testnet é executada automaticamente.
                    </p>
                </div>

                <div style="background:#1e293b; border-radius:16px; padding:22px; margin-bottom:25px;">
                    <h2>Contexto BTC</h2>
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:12px;">
                        <div style="background:#111827; padding:12px; border-radius:10px;">Preço: <strong>{btc["price"]}</strong></div>
                        <div style="background:#111827; padding:12px; border-radius:10px;">Candle 4H: <strong>{btc["candle_4h"]}</strong></div>
                        <div style="background:#111827; padding:12px; border-radius:10px;">Candle 5M: <strong>{btc["candle_5m"]}</strong></div>
                        <div style="background:#111827; padding:12px; border-radius:10px;">Volume 5M: <strong>{btc["volume_5m"]}</strong></div>
                        <div style="background:#111827; padding:12px; border-radius:10px;">Perto Suporte 4H: <strong>{btc["near_support_4h"]}</strong></div>
                        <div style="background:#111827; padding:12px; border-radius:10px;">Perto Resistência 4H: <strong>{btc["near_resistance_4h"]}</strong></div>
                    </div>
                </div>

                <h2>Top Oportunidades do Ciclo</h2>
                {ranking_html}

                <h2 style="margin-top:30px;">Análise dos Ativos</h2>
                {cards_html}

                <div style="background:#1e293b; border-radius:16px; padding:22px; margin-bottom:20px;">
                    <h2>Motor de Risco Educacional</h2>
                    <p>Status: <strong>{risk["status"]}</strong></p>
                    <p>Banca simulada: <strong>{risk["balance_usdt"]} USDT</strong></p>
                    <p>Risco atual simulado: <strong>{risk["current_risk_percent"]}%</strong></p>
                    <p>Operações abertas simuladas: <strong>{risk["open_positions"]}</strong></p>
                    <p>Margem planejada: <strong>{risk["planned_margin_usdt"]} USDT</strong></p>
                    <p>Alavancagem: <strong>{risk["leverage"]}X</strong></p>
                </div>

                <div style="background:#1e293b; border-radius:16px; padding:22px; margin-bottom:20px;">
                    <h2>3X Educacional</h2>
                    <p>Status: <strong>{x3["status"]}</strong></p>
                    <p>Candles 4H contra: <strong>{x3["candles_4h_against"]}</strong></p>
                    <p>Reduce Only: <strong>{x3["reduce_only_rule"]}</strong></p>
                    <p style="color:#fcd34d;">
                        Observação: este 3X ainda é apenas teste educacional. Não representa posição real aberta.
                    </p>
                </div>

                <footer style="color:#94a3b8; margin-top:30px; padding-bottom:30px;">
                    <p>Segurança: nenhuma API Key usada, nenhuma ordem real, nenhuma ordem testnet.</p>
                    <p>Modo atual: OBSERVER.</p>
                    <p>
                        Links:
                        <a href="/status" style="color:#93c5fd;">Status</a> |
                        <a href="/run-json" style="color:#93c5fd;">Run JSON</a> |
                        <a href="/dashboard" style="color:#93c5fd;">Atualizar Dashboard</a>
                    </p>
                </footer>
            </div>
        </body>
    </html>
    """

    return html