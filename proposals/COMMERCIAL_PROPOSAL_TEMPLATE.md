# Proposta Comercial — Local AI Appliance

> **Atenção:** Este documento é um template. Substitua `[Nome do Cliente]`, `[Data]` e demais placeholders.
> **Dados fictícios para demonstração.** Preços são placeholders — consulte proposta comercial vigente.
> Billing é local/manual — não inclui PSP/PIX real.
> SLA depende do plano contratado.

---

**Cliente:** [Nome do Cliente]
**Data:** [Data]
**Proposta Nº:** [Número]
**Validade:** 30 dias
**Responsável:** [Nome do Responsável]

---

## 1. Problema

Sua empresa enfrenta desafios com a adoção de IA generativa:

| Desafio | Impacto |
|---------|---------|
| Dados sensíveis trafegando em APIs públicas | Risco de vazamento, não conformidade LGPD |
| Custos imprevisíveis por token | Dificuldade de orçamento e controle |
| Complexidade técnica para montar infraestrutura local | Time de engenharia desviado do core business |
| Integração trabalhosa com sistemas existentes | Retrabalho e atrasos em projetos |

---

## 2. Solução Proposta

O **Local AI Appliance** é um appliance local de LLM-as-a-Service que oferece:

- **API 100% compatível com OpenAI** — zero retrabalho nas aplicações existentes
- **RAG nativo** — respostas baseadas em documentos internos, sem enviar dados para nuvem
- **TTS local** — síntese de voz sem dependência cloud
- **Portal do Cliente** — autoatendimento para cada tenant (consumo, chaves, faturas)
- **Admin Dashboard** — monitoria completa on-premise
- **Billing local/manual** — faturamento por plano, sem PSP/PIX real
- **Relatórios de readiness e segurança** — suporte à governança de TI

**Tudo roda dentro da sua infraestrutura. Nenhum dado sai da sua rede.**

---

## 3. Benefícios

| Benefício | Descrição |
|-----------|-----------|
| **Privacidade total** | Dados, prompts e documentos nunca saem da sua rede |
| **Custos previsíveis** | Planos com cotas fixas mensais; sem surpresa na fatura |
| **Integração imediata** | OpenAI SDK, LangChain, Open WebUI, n8n — tudo funciona |
| **Soberania de dados** | LGPD e regulamentações setoriais atendidas (com auxílio jurídico) |
| **Autonomia** | Sem dependência de internet, API keys de terceiros ou serviços cloud |
| **Controle granular** | Rate limiting, cotas por cliente, blocking por inadimplência |
| **Suporte local** | Instalação assistida, treinamento, documentação completa |

---

## 4. Planos / Opções

### Planos de Licenciamento

| Recurso | Free | Basic | Pro | Enterprise Local |
|---------|------|-------|-----|------------------|
| **Tokens/mês** | 50.000 | 500.000 | 5.000.000 | 50.000.000 |
| **RPM (req/min)** | 10 | 30 | 60 | 300 |
| **RPD (req/dia)** | 100 | 1.000 | 5.000 | 1.000.000 |
| **Contexto máximo** | 4.096 | 8.192 | 16.384 | 131.072 |
| **Streaming** | Sim | Sim | Sim | Sim |
| **RAG** | Não | 5 docs | 50 docs | 1.000 docs |
| **TTS** | Não | Sim | Sim | Sim |
| **Embeddings** | Não | Sim | Sim | Sim |
| **Exportação de uso** | Não | Não | Sim | Sim |
| **Suporte** | Comunitário | E-mail | E-mail Prioritário | 24/7 Dedicado |
| **Preço mensal*** | Grátis | R$ [ 197 ] | R$ [ 997 ] | Sob consulta |

> *Preços são placeholders. Consulte proposta comercial para valores vigentes.

### Serviços Adicionais (opcionais)

| Serviço | Descrição | Preço |
|---------|-----------|-------|
| Instalação assistida | Implantação remota ou presencial | R$ [ Valor ] |
| Treinamento equipe | 1 dia de treinamento técnico | R$ [ Valor ] |
| Prova de conceito | Ambiente dedicado por 15 dias | R$ [ Valor ] |
| Customização de modelos | Ajuste de parâmetros e templates | Sob consulta |
| Suporte 24/7 adicional | Expansão de SLA | Sob consulta |

---

## 5. Custos — Hardware (Investimento do Cliente)

O appliance roda em hardware fornecido pelo cliente. Abaixo, referências de configuração:

| Configuração | CPU | RAM | GPU | Armazenamento | Custo Estimado* |
|--------------|-----|-----|-----|---------------|-----------------|
| Mínima (testes) | 8 cores | 16 GB | — (CPU) | 100 GB SSD | R$ [ 5.000 ] |
| Recomendada | 8 cores | 32 GB | RTX 4060 12 GB | 500 GB NVMe | R$ [ 15.000 ] |
| Enterprise | 16 cores | 64 GB | RTX 4090 24 GB | 1 TB NVMe | R$ [ 35.000 ] |

> *Custos de hardware são estimativas de mercado. O cliente é responsável pela aquisição e manutenção.

---

## 6. Cronograma

| Fase | Atividade | Prazo |
|------|-----------|-------|
| 1 | Assinatura do contrato | D+0 |
| 2 | Preparação do hardware pelo cliente | D+0 a D+7 |
| 3 | Instalação e configuração | D+8 a D+10 |
| 4 | Validação técnica | D+11 a D+12 |
| 5 | Treinamento | D+13 |
| 6 | Homologação | D+14 a D+20 |
| 7 | Produção | D+21 |

---

## 7. Responsabilidades do Fornecedor

- [x] Fornecer licenciamento do software conforme plano contratado
- [x] Realizar instalação assistida (quando contratada)
- [x] Disponibilizar documentação técnica completa
- [x] Prestar suporte conforme SLA do plano
- [x] Disponibilizar atualizações de versão durante a vigência
- [x] Corrigir bugs críticos em versões estáveis

---

## 8. Responsabilidades do Cliente

- [ ] Providenciar hardware conforme requisitos mínimos
- [ ] Manter sistema operacional e Docker atualizados
- [ ] Realizar backups periódicos (scripts fornecidos)
- [ ] Manter licenciamento em dia
- [ ] Prover acesso remoto para instalação assistida (quando aplicável)
- [ ] Realizar sua própria análise de compliance (LGPD, etc.)
- [ ] Não expor ADMIN_TOKEN ou API keys em locais inseguros
- [ ] Contratar suporte compatível com o nível de criticidade

---

## 9. Suporte

| Nível | Canais | SLA de Resposta | Incluso em |
|-------|--------|-----------------|------------|
| Comunitário | GitHub Issues | Sem SLA | Free |
| E-mail | suporte@provedor.com | 48h úteis | Basic |
| Prioritário | suporte@provedor.com + Chat | 24h úteis | Pro |
| Dedicado | Canais dedicados + Telefone | 2h (crítico), 8h (alto) | Enterprise Local |

> SLA detalhado em contrato específico de suporte.

---

## 10. Próximos Passos

1. [ ] Revisar esta proposta internamente
2. [ ] Agendar call técnica para esclarecimentos
3. [ ] Definir plano e serviços adicionais
4. [ ] Assinar contrato e ordem de serviço
5. [ ] Iniciar preparação do ambiente
6. [ ] Agendar instalação

---

**Esta proposta é confidencial e de uso exclusivo do cliente.**
**Preços são placeholders — consulte proposta comercial vigente.**
**Billing é local/manual — não inclui PSP/PIX real.**
**Este documento não substitui análise jurídica ou de compliance.**


--- 
*Nota: Esta é uma ESTIMATIVA LOCAL gerada para fins de demonstração. Valores sujeitos a alteração após análise de escopo.*
