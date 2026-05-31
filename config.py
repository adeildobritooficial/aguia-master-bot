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
# Para Render gratuito, 10 é um bom começo.
MAX_AUTO_SYMBOLS = 10

# Mínimo de ativos aceitos na seleção automática.
# Se vier menos que isso, usa fallback.
MIN_SYMBOLS_REQUIRED = 5

# Ativar lista branca operacional
# Isso impede o robô de analisar moedas estranhas da Testnet.
USE_OPERATIONAL_WHITELIST = True

# Lista branca de ativos com maior potencial operacional.
# O robô só aceitará ativos que estejam aqui.
OPERATIONAL_WHITELIST = [
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
    "DOTUSDT",
    "TRXUSDT",
    "NEARUSDT",
    "APTUSDT",
    "SUIUSDT",
    "INJUSDT",
    "AAVEUSDT",
    "UNIUSDT",
    "ETCUSDT",
    "ATOMUSDT",
    "FILUSDT",
    "OPUSDT",
    "ARBUSDT",
    "SEIUSDT",
    "TIAUSDT",
    "WLDUSDT",
    "FETUSDT",
    "GALAUSDT",
    "IMXUSDT",
    "RUNEUSDT",
]

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