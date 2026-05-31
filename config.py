# config.py

# ============================================================
# ÁGUIA MASTER BOT — CONFIGURAÇÕES GERAIS
# ============================================================

# Modo inicial do robô
# Nesta fase, o robô NÃO executa ordens.
BOT_MODE = "OBSERVER"

# Corretora usada na primeira fase
EXCHANGE = "BINANCE"

# Ambiente inicial
ENVIRONMENT = "BINANCE_FUTURES_TESTNET_PUBLIC_DATA"

# ============================================================
# SELEÇÃO DE ATIVOS
# ============================================================

# Buscar automaticamente os melhores ativos por volume
USE_AUTO_SYMBOL_SELECTION = True

# Quantidade máxima de ativos que o robô vai analisar por ciclo
# Começamos com 10 para não pesar no Render gratuito.
MAX_AUTO_SYMBOLS = 10

# Lista fixa de segurança caso a busca automática falhe
FALLBACK_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "XRPUSDT",
    "BNBUSDT",
    "DOGEUSDT",
    "ADAUSDT",
    "AVAXUSDT",
    "LINKUSDT",
    "LTCUSDT",
]

# ============================================================
# TIMEFRAMES
# ============================================================

TIMEFRAME_4H = "4h"
TIMEFRAME_5M = "5m"

# Quantidade de candles analisados
LIMIT_4H = 80
LIMIT_5M = 120

# ============================================================
# REGRAS INICIAIS DE RISCO
# ============================================================

MAX_RISK_PERCENT = 7.0
BLOCK_RISK_PERCENT = 10.0
KILL_SWITCH_RISK_PERCENT = 15.0

# ============================================================
# CONFIGURAÇÃO DO MÉTODO
# ============================================================

USE_BTC_AS_MARKET_FILTER = True
REQUIRE_RETEST_FOR_ENTRY = True
REQUIRE_VOLUME_CONFIRMATION = True

# ============================================================
# REGRAS DO 3X
# ============================================================

ENABLE_3X_ANALYSIS = True
MIN_4H_CANDLES_FOR_3X = 8
MAX_4H_CANDLES_FOR_3X = 15

# ============================================================
# REDUCE ONLY
# ============================================================

REQUIRE_REDUCE_ONLY_ON_EXITS = True