# CHECKLIST DE SEGURANÇA — ÁGUIA MASTER BOT

## Objetivo

Este checklist define as travas obrigatórias antes de qualquer avanço operacional do ÁGUIA MASTER BOT.

Regra suprema:

**Proteção da banca vem antes de qualquer possibilidade de lucro.**

Nenhuma etapa de execução, seja simulação, Testnet ou real, pode avançar sem validação de segurança.

---

## 1. Segurança de ambiente

- [x] GitHub Codespaces configurado
- [x] Render configurado
- [x] Python local no PC funcionando
- [x] Binance Futures Demo/Testnet conectada localmente
- [x] Render com variáveis de ambiente configuradas
- [x] Render bloqueado pela Binance para diagnóstico privado por localização restrita
- [x] Diagnóstico privado Binance Testnet validado localmente no PC
- [x] Dashboard online no Render
- [x] Dashboard online localmente

---

## 2. Segurança de chaves API

- [x] API Key não está no código
- [x] API Secret não está no código
- [x] API Key não foi publicada no GitHub
- [x] API Secret não foi publicada no GitHub
- [x] API Testnet configurada via variáveis de ambiente
- [x] Arquivo `.env` local não deve ser enviado ao GitHub
- [ ] Confirmar que a API não possui permissão de saque
- [ ] Confirmar que a API usada é Testnet/Demo
- [ ] Confirmar que não existe API real configurada no Render
- [ ] Confirmar que não existe API real configurada no `.env` local

---

## 3. Segurança de execução

- [x] `TRADING_ENABLED=false`
- [x] `REAL_TRADING_ENABLED=false`
- [x] `HUMAN_CONFIRM_REQUIRED=true`
- [x] Ordens reais bloqueadas
- [x] Ordens Testnet bloqueadas nesta fase
- [x] `/health` retorna ordens bloqueadas
- [x] `/api/safety-status` retorna `SEGURO_BLOQUEADO`
- [x] `/api/config-status` retorna `CONFIG_SEGURA`
- [x] `/api/system-status` retorna `ONLINE_SEGURO`
- [ ] Nenhum executor real implementado
- [ ] Nenhum executor Testnet automático liberado
- [ ] Nenhuma ordem automática permitida

---

## 4. Segurança do dashboard

- [x] Dashboard Render funcionando
- [x] Dashboard local funcionando
- [x] Dashboard não executa ordens
- [x] Dashboard mostra avisos de segurança
- [x] Dashboard mantém real bloqueado
- [x] Dashboard mantém Testnet bloqueada nesta fase
- [ ] Adicionar card visual do System Status Engine
- [ ] Adicionar card visual do Config Status Engine
- [ ] Adicionar card visual do Safety Status Engine
- [ ] Adicionar botão visual de Kill Switch futuramente

---

## 5. Segurança do código

- [x] `STATUS_PROJETO.md` criado
- [x] `REVISAO_APP.md` criado
- [x] `ENDPOINTS.md` criado
- [x] `core/` criado
- [x] `core/safety_status_engine.py` criado
- [x] `core/config_status_engine.py` criado
- [x] `core/system_status_engine.py` criado
- [x] Rotas de status testadas no Codespaces
- [x] Rotas de status testadas no Render
- [ ] Separar próximos módulos sem quebrar o `app.py`
- [ ] Criar testes automatizados
- [ ] Criar logs persistentes
- [ ] Criar banco de dados

---

## 6. Segurança de risco

- [x] Risk Engine inicial existe
- [x] Limite máximo de risco configurado
- [x] Limite de bloqueio configurado
- [x] Limite de Kill Switch configurado
- [x] Reduce Only obrigatório em saídas definido no config
- [ ] Risk Engine profissional ainda pendente
- [ ] Validação de risco por operação ainda pendente
- [ ] Validação de risco diário ainda pendente
- [ ] Validação de risco semanal ainda pendente
- [ ] Bloqueio por liquidação próxima ainda pendente
- [ ] Bloqueio por excesso de posições ainda pendente

---

## 7. Segurança do 3X

- [x] 3X existe apenas como análise educacional
- [x] 3X não executa ordens
- [x] 3X automático bloqueado
- [x] Reduce Only obrigatório após 3X
- [ ] Criar X3 Simulator avançado
- [ ] Bloquear 3X emocional
- [ ] Bloquear 3X sem candle contrário validado
- [ ] Bloquear 3X sem confirmação humana
- [ ] Bloquear 3X sem plano de saída

---

## 8. Segurança de Reconciliation

- [ ] Reconciliation Engine ainda não criado
- [ ] Comparar posições internas versus Binance
- [ ] Comparar ordens internas versus Binance
- [ ] Comparar saldo esperado versus saldo da Binance
- [ ] Pausar se houver divergência
- [ ] Acionar Kill Switch se divergência for crítica

---

## 9. Segurança de Kill Switch

- [ ] Kill Switch Engine ainda não criado
- [ ] Botão visual no dashboard ainda pendente
- [ ] Bloqueio por perda diária ainda pendente
- [ ] Bloqueio por perda semanal ainda pendente
- [ ] Bloqueio por erro de API ainda pendente
- [ ] Bloqueio por ordem desconhecida ainda pendente
- [ ] Bloqueio por posição desconhecida ainda pendente
- [ ] Bloqueio por tentativa de real indevida ainda pendente

---

## 10. Segurança antes de Simulação

Antes de avançar para simulação local completa, precisa estar aprovado:

- [x] Dashboard funcionando
- [x] Status de segurança funcionando
- [x] Config Status funcionando
- [x] System Status funcionando
- [x] Endpoints documentados
- [x] Status do projeto atualizado
- [ ] Checklist de segurança criado e salvo
- [ ] Simulação ainda sem execução real ou Testnet
- [ ] Logs de simulação definidos

---

## 11. Segurança antes de Testnet com ordem

Antes de qualquer ordem Testnet, precisa estar aprovado:

- [ ] Simulation Engine funcionando
- [ ] Order Plan Engine profissional funcionando
- [ ] Human Confirm Engine funcionando
- [ ] Risk Engine profissional funcionando
- [ ] Reduce Only Guard funcionando
- [ ] Position Manager funcionando
- [ ] Reconciliation Engine funcionando
- [ ] Kill Switch Engine funcionando
- [ ] Logs persistentes funcionando
- [ ] Testes automatizados mínimos passando
- [ ] Confirmação humana obrigatória ativa
- [ ] `TRADING_ENABLED` validado com extremo cuidado
- [ ] `REAL_TRADING_ENABLED=false`

---

## 12. Segurança antes de real

Antes de qualquer operação real, precisa estar aprovado:

- [ ] Testnet validada por tempo suficiente
- [ ] Histórico de simulação analisado
- [ ] Histórico Testnet analisado
- [ ] Relatórios operacionais funcionando
- [ ] Nenhum erro crítico recente
- [ ] Nenhuma divergência de saldo
- [ ] Nenhuma posição desconhecida
- [ ] Nenhuma ordem desconhecida
- [ ] Kill Switch testado
- [ ] Reconciliation testado
- [ ] Reduce Only testado
- [ ] Confirmação humana testada
- [ ] Real Executor bloqueado criado
- [ ] Checklist de maturidade aprovado
- [ ] Decisão emocional descartada
- [ ] Banca de dinheiro essencial proibida

---

## 13. Decisão atual

DECISÃO: AGUARDAR  
ROBÔ: ÁGUIA MASTER BOT  
AMBIENTE: BINANCE FUTURES TESTNET / RENDER / LOCAL  
CORRETORA: BINANCE  
ATIVO: TODOS  
DIREÇÃO: NONE  
RISCO: CONTROLADO  
MOTIVO: Robô ainda em fase de organização e segurança.  
TRAVAS: Ordens reais e Testnet bloqueadas.  
AÇÃO SEGURA: Continuar organização modular e documentação.  
CONFIRMAÇÃO HUMANA: Obrigatória em futuras etapas operacionais.

---

## 14. Próximo passo permitido

Próximo passo permitido após este checklist:

- Atualizar `STATUS_PROJETO.md`
- Atualizar `ENDPOINTS.md` se necessário
- Começar preparação para o próximo módulo seguro
- Não criar executor de ordens ainda
- Não ativar trading
- Não alterar variáveis de execução