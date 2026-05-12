# Acceptance Criteria — Local AI Appliance

> **AVISO JURÍDICO:** Este documento é um **template genérico** fornecido apenas para fins de referência e pré-alinhamento comercial. Não constitui aconselhamento jurídico, não cria vínculo contratual e **não dispensa revisão por assessoria jurídica qualificada**. O uso deste template não garante compliance automático com qualquer norma ou regulação.

## 1. Objetivo

Este documento define os critérios objetivos para aceitação da implantação do **LLM Inference Stack** em modo **Local Appliance** no ambiente da CONTRATANTE. O aceite formal deve ser assinado por ambas as partes após verificação de cada item.

## 2. Critérios de Aceite Obrigatórios

### 2.1. Infraestrutura

- [ ] Docker Engine 24+ e Docker Compose V2 estão instalados e funcionais.
- [ ] O hardware atende ou excede os requisitos mínimos especificados no SOW.
- [ ] As portas necessárias estão liberadas no firewall da CONTRATANTE.
- [ ] O sistema operacional está atualizado e em versão suportada.

### 2.2. Implantação

- [ ] `docker compose ps` exibe todos os serviços com status `Up (healthy)`.
- [ ] Nenhum container está em estado de restart loop ou crash.
- [ ] Os volumes de dados estão mapeados corretamente e persistentes.

### 2.3. Saúde do Sistema

- [ ] `GET /health` retorna HTTP 200 com body contendo `{"status": "ok"}`.
- [ ] `GET /ready` retorna HTTP 200 indicando que o sistema está pronto para receber requisições.
- [ ] `GET /status` retorna métricas de utilização sem erros.

### 2.4. Inferência

- [ ] `POST /v1/chat/completions` com payload mínimo retorna HTTP 200 com resposta válida.
- [ ] O modelo padrão carregado responde com coerência mínima (teste de sanidade).
- [ ] Streaming (SSE) funciona corretamente quando habilitado.

### 2.5. Módulos Contratados (conforme plano)

- [ ] **RAG:** Upload de documento e consulta com contexto retornam resultados coerentes.
- [ ] **TTS:** Conversão de texto para áudio retorna arquivo de áudio válido.
- [ ] **Embeddings:** Geração de embeddings retorna vetores de dimensão esperada.
- [ ] **Visão:** Análise de imagem retorna descrição coerente.

### 2.6. Autenticação e Multi-Tenancy

- [ ] Criação de cliente/tenant via API retorna sucesso.
- [ ] Tokens de API funcionam e são validados corretamente.
- [ ] Isolamento entre tenants é respeitado (dados do Tenant A não acessíveis ao Tenant B).

### 2.7. Documentação

- [ ] Guia de operação do sistema foi entregue em formato digital.
- [ ] Credenciais de acesso inicial foram fornecidas de forma segura.
- [ ] Procedimentos de backup e restauração foram demonstrados.

### 2.8. Treinamento

- [ ] Sessão de transferência de conhecimento foi realizada.
- [ ] A equipe da CONTRATANTE consegue realizar operações básicas (iniciar/parar serviços, verificar logs, consultar status).

## 3. Procedimento de Aceite

1. A CONTRATADA notifica a CONTRATANTE que a implantação está concluída.
2. A CONTRATANTE realiza a verificação de cada item deste checklist em até [10] dias úteis.
3. Caso todos os critérios obrigatórios sejam atendidos, a CONTRATANTE emite o **Termo de Aceite** formal.
4. Caso haja não conformidades, a CONTRATADA terá [15] dias úteis para corrigir, e nova verificação será agendada.
5. O silêncio da CONTRATANTE por mais de [20] dias úteis após a notificação será interpretado como aceite tácito, salvo disposição em contrário no contrato principal.

## 4. Não Conformidades

Caso um ou mais critérios de aceite não sejam atendidos:

- A CONTRATADA deve apresentar um plano de ação corretiva.
- O cronograma de correção deve ser acordado entre as partes.
- Itens não críticos podem ser aceitos com ressalvas, mediante acordo escrito.

## 5. Aceite Parcial

A CONTRATANTE pode emitir aceite parcial para entregáveis específicos, desde que:

- O item em questão atenda integralmente aos critérios definidos.
- O aceite parcial não dependa de itens ainda não concluídos.
- Os itens não aceitos estejam documentados e com plano de correção acordado.

## 6. Revisão Jurídica Obrigatória

**ESTE DOCUMENTO É UM TEMPLATE E DEVE SER REVISADO POR ASSESSORIA JURÍDICA QUALIFICADA ANTES DE QUALQUER ASSINATURA.**

- A CONTRATADA não oferece aconselhamento jurídico por meio deste template.
- Nenhuma garantia absoluta de compliance regulatório é fornecida.
- Recomenda-se a consulta a um advogado especializado antes da celebração.

---

*Template Acceptance Criteria v1.0 — Gerado em {{DATE}} — O conteúdo deste arquivo é um modelo de referência e não constitui documento contratual válido sem revisão jurídica.*
