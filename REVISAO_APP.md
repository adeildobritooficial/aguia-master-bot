# REVISÃO DO APP.PY — ÁGUIA MASTER BOT

## Objetivo da revisão

Mapear a estrutura atual do arquivo `app.py` antes de qualquer refatoração, para evitar quebrar o robô que já está funcionando no Render e localmente.

## Status atual

O arquivo `app.py` está funcionando, porém concentra muitas responsabilidades em um único arquivo.

Ele atualmente cuida de:

- Rotas Flask
- Dashboard
- Health check
- Relatórios
- Diagnóstico Binance Testnet
- Plano seguro de ordem
- Confirmação humana
- Validação final de risco
- Simulação Testnet
- Autorização manual de teste
- Executor didático Testnet controlado
- Autorização final de execução Testnet
- Motor de decisão MEC

## Rotas identificadas

- `/`
- `/dashboard`
- `/api/report`
- `/api/binance-testnet`
- `/api/order-plan`
- `/api/human-confirm`
- `/api/risk-final-validation`
- `/api/testnet-simulation`
- `/api/manual-test-authorization`
- `/api/controlled-testnet-executor`
- `/api/final-testnet-execution-authorization`
- `/api/mec-decision-engine`
- `/health`

## Diagnóstico técnico

O `app.py` está funcional, mas está grande demais para a próxima fase profissional do robô.

Riscos de manter tudo no mesmo arquivo:

- Dificuldade de manutenção
- Risco de duplicação de lógica
- Risco de alterar dashboard e quebrar decisão operacional
- Risco de misturar visualização com execução
- Dificuldade para criar testes automatizados
- Dificuldade para evoluir Testnet Executor, Reconciliation e Kill Switch

## Decisão técnica

Não vamos apagar nada agora.

A refatoração será gradual, segura e com testes.

A primeira separação recomendada será:

1. Manter `app.py` como entrada Flask e registro de rotas
2. Criar pasta `core/`
3. Mover gradualmente funções de decisão, risco, simulação e confirmação para módulos separados
4. Manter rotas chamando funções externas
5. Testar `/health`, `/dashboard` e APIs após cada mudança
6. Fazer commit pequeno a cada alteração

## Estrutura futura recomendada

```text
core/
├── mec_decision_engine.py
├── order_plan_engine.py
├── human_confirm_engine.py
├── testnet_simulation_engine.py
├── risk_final_validator.py
├── controlled_testnet_executor.py
├── report_engine.py
└── safety_status_engine.py