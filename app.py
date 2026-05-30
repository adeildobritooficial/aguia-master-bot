# app.py

from fastapi import FastAPI
from datetime import datetime

from main import run_observer

app = FastAPI(
    title="ÁGUIA MASTER BOT",
    description="Robô observador do Método Águia Cripto em modo seguro.",
    version="1.0.0",
)


@app.get("/")
def home():
    return {
        "name": "ÁGUIA MASTER BOT",
        "status": "online",
        "mode": "observer",
        "message": "Robô online. Nenhuma ordem é executada nesta fase.",
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
    try:
        run_observer()
        return {
            "status": "success",
            "message": "Ciclo do robô observador executado com sucesso.",
            "orders_executed": False,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
    except Exception as error:
        return {
            "status": "error",
            "message": "O robô encontrou um erro e não executou nenhuma ordem.",
            "error": str(error),
            "orders_executed": False,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }