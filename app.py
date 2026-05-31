# app.py

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from datetime import datetime

from main import run_observer

app = FastAPI(
    title="ÁGUIA MASTER BOT",
    description="Robô observador do Método Águia Cripto em modo seguro.",
    version="1.2.0",
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
    """
    Mantém compatibilidade com a rota antiga.
    Agora retorna o relatório completo.
    """
    return run_observer()


@app.get("/run-json")
def run_json():
    """
    Rota técnica para obter o relatório completo em JSON.
    """
    return run_observer()


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    """
    Painel visual simples do ÁGUIA MASTER BOT.
    """
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

    cards_html = ""

    for item in report["summary"]:
        decision = item["decision"]

        if "LONG" in decision:
            color = "#16a34a"
        elif "SHORT" in decision:
            color = "#dc2626"
        elif "AGUARDAR" in decision:
            color = "#f59e0b"
        else:
            color = "#6b7280"

        reasons = "".join([f"<li>{reason}</li>" for reason in item["reasons"]])
        warnings = "".join([f"<li>{warning}</li>" for warning in item["warnings"]])

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
            <ul>{reasons}</ul>

            <h3 style="color:#fcd34d;">Alertas</h3>
            <ul>{warnings}</ul>
        </div>
        """

    risk = report["risk"]
    x3 = report["x3"]
    btc = report["btc_context"]

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