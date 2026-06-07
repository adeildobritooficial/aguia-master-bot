# ENDPOINTS — ÁGUIA MASTER BOT

## Objetivo

Documentar as rotas atuais do robô para facilitar manutenção, testes e refatoração segura.

## Rotas principais

### `/`

Página inicial simples do robô.

Status:
- Funcional
- Não executa ordens

---

### `/dashboard`

Dashboard principal do ÁGUIA MASTER BOT.

Status:
- Funcional
- Não executa ordens

---

### `/health`

Endpoint de saúde do sistema.

Uso:
- Verificar se o app está online
- Confirmar se ordens estão bloqueadas

Status esperado:
- `orders_enabled: false`
- `real_orders_enabled: false`
- `testnet_orders_enabled: false`

---

### `/api/report`

API de relatório geral do robô.

Status:
- Funcional
- Não executa ordens

---

### `/api/binance-testnet`

Diagnóstico Binance Futures Demo/Testnet.

Observações:
- Funciona localmente no PC
- No Render pode ser bloqueado pela Binance por localização restrita
- Não executa ordens

Status seguro esperado:
- `use_testnet: true`
- `has_api_key: true`
- `has_api_secret: true`
- `trading_enabled: false`
- `real_orders_enabled: false`
- `testnet_orders_enabled: false`

---

### `/api/order-plan`

Exibe proposta segura de plano de ordem.

Status:
- Didático/controlado
- Não executa ordens

---

### `/api/human-confirm`

Exibe modelo de confirmação humana.

Status:
- Didático/controlado
- Não executa ordens

---

### `/api/risk-final-validation`

Exibe validação final de risco.

Status:
- Didático/controlado
- Não executa ordens

---

### `/api/testnet-simulation`

Exibe simulação educacional Testnet.

Status:
- Simulação
- Não executa ordens reais
- Não executa ordens Testnet nesta fase

---

### `/api/manual-test-authorization`

Exibe autorização manual de teste.

Status:
- Didático/controlado
- Não executa ordens

---

### `/api/controlled-testnet-executor`

Exibe executor didático Testnet controlado.

Status:
- Didático/controlado
- Não executa ordens nesta fase

---

### `/api/final-testnet-execution-authorization`

Exibe autorização final educacional para execução Testnet.

Status:
- Didático/controlado
- Não executa ordens nesta fase

---

### `/api/mec-decision-engine`

Exibe motor de decisão MEC em formato API.

Status:
- Didático/controlado
- Não executa ordens

---

### `/api/safety-status`

Exibe status centralizado de segurança operacional.

Status:
- Funcional no Codespaces
- Funcional no Render
- Não consulta corretora
- Não executa ordens

Status seguro esperado:
- `status: SEGURO_BLOQUEADO`
- `trading_enabled: false`
- `real_orders_enabled: false`
- `testnet_orders_enabled: false`
- `human_confirm_required: true`

---

### `/api/config-status`

Exibe o status seguro das configurações operacionais do robô.

Status:
- Funcional no Codespaces
- Funcional no Render
- Não consulta corretora
- Não executa ordens

Status seguro esperado:
- `config_safety_status: CONFIG_SEGURA`
- `binance_use_testnet: true`
- `trading_enabled: false`
- `real_trading_enabled: false`
- `human_confirm_required: true`
- `safety_blockers: []`

## Regra geral

Nenhum endpoint pode executar ordens enquanto:

- `TRADING_ENABLED=false`
- `REAL_TRADING_ENABLED=false`
- `HUMAN_CONFIRM_REQUIRED=true`
- Reconciliation Engine ainda não estiver concluído
- Kill Switch Engine ainda não estiver concluído
- Checklist de maturidade ainda não estiver aprovado