import os
import time
import hmac
import hashlib
from urllib.parse import urlencode

import requests


BINANCE_DEMO_FAPI_BASE_URL = "https://demo-fapi.binance.com"
BINANCE_REAL_FAPI_BASE_URL = "https://fapi.binance.com"


class BinanceFuturesConnector:
    """
    Conector seguro para Binance Futures Demo/Testnet.

    Nesta fase:
    - consulta status da API
    - consulta horário do servidor
    - consulta saldo
    - consulta posições
    - consulta ordens abertas

    Não executa ordens automaticamente.
    """

    def __init__(self):
        self.api_key = os.getenv("BINANCE_TESTNET_API_KEY", "")
        self.api_secret = os.getenv("BINANCE_TESTNET_API_SECRET", "")
        self.use_testnet = os.getenv("BINANCE_USE_TESTNET", "true").lower() == "true"
        self.trading_enabled = os.getenv("TRADING_ENABLED", "false").lower() == "true"
        self.human_confirm_required = os.getenv("HUMAN_CONFIRM_REQUIRED", "true").lower() == "true"
        self.operation_target = os.getenv("OPERATION_TARGET", "BINANCE_FUTURES_TESTNET")

        if self.use_testnet:
            self.base_url = BINANCE_DEMO_FAPI_BASE_URL
            self.environment = "BINANCE FUTURES DEMO/TESTNET"
        else:
            self.base_url = BINANCE_REAL_FAPI_BASE_URL
            self.environment = "BINANCE FUTURES REAL"

    def has_credentials(self):
        return bool(self.api_key and self.api_secret)

    def headers(self):
        return {
            "X-MBX-APIKEY": self.api_key
        }

    def sign_params(self, params):
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        params["signature"] = signature
        return params

    def public_get(self, path, params=None, timeout=10):
        url = f"{self.base_url}{path}"

        try:
            response = requests.get(url, params=params or {}, timeout=timeout)
            return {
                "ok": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.text else {},
                "raw": response.text[:500]
            }
        except Exception as error:
            return {
                "ok": False,
                "status_code": 0,
                "data": {},
                "raw": str(error)
            }

    def signed_get(self, path, params=None, timeout=10):
        if not self.has_credentials():
            return {
                "ok": False,
                "status_code": 0,
                "data": {},
                "raw": "API Key ou Secret Key não configuradas."
            }

        params = params or {}
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = 5000

        signed_params = self.sign_params(params)

        url = f"{self.base_url}{path}"

        try:
            response = requests.get(
                url,
                params=signed_params,
                headers=self.headers(),
                timeout=timeout
            )

            return {
                "ok": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.text else {},
                "raw": response.text[:800]
            }
        except Exception as error:
            return {
                "ok": False,
                "status_code": 0,
                "data": {},
                "raw": str(error)
            }

    def get_server_time(self):
        return self.public_get("/fapi/v1/time")

    def ping(self):
        return self.public_get("/fapi/v1/ping")

    def get_account(self):
        return self.signed_get("/fapi/v2/account")

    def get_balance(self):
        return self.signed_get("/fapi/v2/balance")

    def get_positions(self):
        account = self.get_account()

        if not account.get("ok"):
            return {
                "ok": False,
                "positions": [],
                "error": account.get("raw")
            }

        positions = account.get("data", {}).get("positions", [])

        open_positions = []

        for position in positions:
            try:
                position_amt = float(position.get("positionAmt", 0))

                if position_amt != 0:
                    open_positions.append(
                        {
                            "symbol": position.get("symbol"),
                            "positionAmt": position.get("positionAmt"),
                            "entryPrice": position.get("entryPrice"),
                            "markPrice": position.get("markPrice"),
                            "unRealizedProfit": position.get("unRealizedProfit"),
                            "leverage": position.get("leverage"),
                            "positionSide": position.get("positionSide"),
                        }
                    )
            except Exception:
                continue

        return {
            "ok": True,
            "positions": open_positions,
            "count": len(open_positions)
        }

    def get_open_orders(self, symbol=None):
        params = {}

        if symbol:
            params["symbol"] = symbol

        result = self.signed_get("/fapi/v1/openOrders", params=params)

        if not result.get("ok"):
            return {
                "ok": False,
                "orders": [],
                "error": result.get("raw")
            }

        orders = result.get("data", [])

        return {
            "ok": True,
            "orders": orders,
            "count": len(orders)
        }

    def get_usdt_balance_summary(self):
        balance = self.get_balance()

        if not balance.get("ok"):
            return {
                "ok": False,
                "asset": "USDT",
                "balance": 0,
                "availableBalance": 0,
                "crossWalletBalance": 0,
                "error": balance.get("raw")
            }

        balances = balance.get("data", [])

        for item in balances:
            if item.get("asset") == "USDT":
                return {
                    "ok": True,
                    "asset": "USDT",
                    "balance": item.get("balance"),
                    "availableBalance": item.get("availableBalance"),
                    "crossWalletBalance": item.get("crossWalletBalance"),
                    "maxWithdrawAmount": item.get("maxWithdrawAmount"),
                }

        return {
            "ok": False,
            "asset": "USDT",
            "balance": 0,
            "availableBalance": 0,
            "crossWalletBalance": 0,
            "error": "USDT não encontrado na conta."
        }

    def diagnostic(self):
        ping = self.ping()
        server_time = self.get_server_time()
        account = self.get_account()
        balance = self.get_usdt_balance_summary()
        positions = self.get_positions()
        open_orders = self.get_open_orders()

        connected = (
            ping.get("ok")
            and server_time.get("ok")
            and account.get("ok")
        )

        safety_status = "BLOQUEADO PARA EXECUÇÃO"

        if self.trading_enabled and self.human_confirm_required:
            safety_status = "EXECUÇÃO TESTNET SOMENTE COM CONFIRMAÇÃO HUMANA"

        if self.trading_enabled and not self.human_confirm_required:
            safety_status = "PERIGO: EXECUÇÃO SEM CONFIRMAÇÃO HUMANA"

        return {
            "connector": "BINANCE FUTURES",
            "environment": self.environment,
            "operation_target": self.operation_target,
            "base_url": self.base_url,
            "has_api_key": bool(self.api_key),
            "has_api_secret": bool(self.api_secret),
            "use_testnet": self.use_testnet,
            "trading_enabled": self.trading_enabled,
            "human_confirm_required": self.human_confirm_required,
            "safety_status": safety_status,
            "connected": connected,
            "ping": {
                "ok": ping.get("ok"),
                "status_code": ping.get("status_code"),
                "raw": ping.get("raw")
            },
            "server_time": {
                "ok": server_time.get("ok"),
                "status_code": server_time.get("status_code"),
                "data": server_time.get("data"),
                "raw": server_time.get("raw")
            },
            "account": {
                "ok": account.get("ok"),
                "status_code": account.get("status_code"),
                "raw": account.get("raw") if not account.get("ok") else "Conta acessada com sucesso."
            },
            "balance": balance,
            "positions": positions,
            "open_orders": open_orders,
            "orders_enabled_now": False,
            "real_orders_enabled": False,
            "testnet_orders_enabled": False,
            "message": "Conector em modo seguro. Nenhuma ordem é executada nesta fase."
        }


def get_binance_testnet_diagnostic():
    connector = BinanceFuturesConnector()
    return connector.diagnostic()