---
owner: platform-ops
status: consolidated
---

# Roteiro de Apresentação (Demo Script)

Este documento fornece um guia passo a passo para realizar uma apresentação comercial ou técnica do `llm-inference-stack`.

## 1. Abertura
**Fala:** "Olá, hoje vou apresentar o llm-inference-stack. Esta é uma plataforma local de inferência de LLM (Large Language Models) projetada para empresas que buscam soberania total sobre seus dados, performance consistente e controle de custos, sem depender de APIs de nuvem pública."

## 2. Visão Geral da Infraestrutura
**Ação:** Mostre o terminal com os containers rodando ou o comando `docker ps`.
**Fala:** "Aqui temos a stack rodando localmente. Utilizamos Docker para isolar o Control Plane (nossa camada de governança e API) do Data Plane (onde o modelo de IA realmente executa). Tudo isso pode rodar em um servidor on-premise ou até mesmo em uma estação de trabalho potente."

## 3. Governança e Administração
**Ação:** Abra o **Admin Dashboard** (`http://localhost:18080/admin-dashboard`).
**Fala:** "Como administrador, você tem visão total sobre a saúde do sistema, o uso de tokens por cliente e a latência das respostas. Podemos identificar gargalos ou abusos em tempo real."

**Ação:** Vá para o **Admin Lab** (`http://localhost:18080/admin-lab`) e mostre a aba de **Modelos**.
**Fala:** "O sistema permite gerenciar múltiplos modelos e backends. Podemos trocar o modelo default ou adicionar novos arquivos GGUF sem precisar reescrever as aplicações que consomem a API."

## 4. Experiência do Cliente
**Ação:** Abra o **Client Portal** (`http://localhost:18080/client-portal`).
**Fala:** "Cada cliente (ou departamento interno) tem seu próprio portal. Aqui eles podem gerar suas chaves de API, monitorar seu consumo diário e mensal em relação às cotas estabelecidas, e visualizar suas faturas."

## 5. Integração com Desenvolvedores
**Ação:** Execute uma chamada `curl` no terminal demonstrando compatibilidade OpenAI.
**Fala:** "Para os desenvolvedores, a transição é transparente. Nossa API é 100% compatível com o padrão OpenAI. Basta trocar a URL base e a API Key, e qualquer aplicação existente funcionará imediatamente com nossos modelos locais."

## 6. Inteligência sobre Dados Próprios (RAG)
**Ação:** Execute uma query RAG via terminal ou mostre a aba de documentos no portal.
**Fala:** "Além da inferência pura, oferecemos suporte nativo a RAG (Retrieval-Augmented Generation). Podemos indexar documentos internos da empresa para que o modelo responda com base em informações privadas e atualizadas, garantindo que nenhum dado sensível saia da infraestrutura da companhia."

## 7. Controle Financeiro e Billing
**Ação:** Mostre uma fatura no Admin Lab e marque-a como paga.
**Fala:** "Mesmo em ambientes locais, o controle de custos é vital. O sistema gera faturas baseadas no consumo real. Podemos gerenciar o faturamento de forma manual ou integrada, permitindo um modelo de 'chargeback' interno ou venda de serviços."

## 8. Confiabilidade e Validação
**Ação:** Execute `./scripts/validate-demo-local.sh`.
**Fala:** "Para garantir que tudo está operando como esperado, temos ferramentas de validação automatizada que testam desde a conectividade do banco de dados até a qualidade da resposta do modelo."

## 9. Encerramento
**Fala:** "Em resumo, o llm-inference-stack entrega o poder dos modelos de linguagem modernos com a segurança de uma infraestrutura privada. Alguma dúvida sobre como podemos adaptar isso ao seu cenário?"
