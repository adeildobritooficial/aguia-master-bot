# config.py

# Modo inicial do robô
# Nesta primeira fase, o robô NÃO executa ordens.
# Ele apenas observa o mercado e gera decisões.
BOT_MODE = "OBSERVER"

# Corretora usada na primeira fase
EXCHANGE = "BINANCE"

# Ambiente inicial
# IMPORTANTE: começaremos sem conta real.
ENVIRONMENT = "PUBLIC_MARKET_DATA"

# Ativos que o robô vai observar
SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
]

# Timeframes principais do método
TIMEFRAME_4H = "4h"
TIMEFRAME_5M = "5m"

# Quantidade de candles analisados
LIMIT_4H = 80
LIMIT_5M = 120

# Regras iniciais de risco educacional
MAX_RISK_PERCENT = 7.0
BLOCK_RISK_PERCENT = 10.0
KILL_SWITCH_RISK_PERCENT = 15.0

# Configuração do método
USE_BTC_AS_MARKET_FILTER = True
REQUIRE_RETEST_FOR_ENTRY = True
REQUIRE_VOLUME_CONFIRMATION = True

# Regras do 3X
ENABLE_3X_ANALYSIS = True
MIN_4H_CANDLES_FOR_3X = 8
MAX_4H_CANDLES_FOR_3X = 15

# Reduce Only
REQUIRE_REDUCE_ONLY_ON_EXITS = True