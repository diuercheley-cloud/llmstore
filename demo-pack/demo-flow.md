# Roteiro de Demonstração Comercial

Tempo estimado: **30-45 minutos**

## Preparação (5 min antes)

```bash
# 1. Verificar se a stack está rodando
make health

# 2. Resetar dados demo anteriores (se necessário)
./scripts/dev/seed-commercial-demo-pack.sh --reset

# 3. Carregar demo pack
make demo-pack

# 4. Verificar tudo funcionando
make validate-demo-pack
```

## Abertura (2 min)

"Vou mostrar uma plataforma completa de IA que roda **100% local** no seu hardware. Sem enviar dados para nuvem, sem dependência de internet, sem custo por token."

## 1. Visão Geral da Stack (3 min)

- Acessar **Admin Dashboard** (`http://localhost:18080/admin-dashboard`)
- Mostrar métricas de saúde: backends online, modelos carregados
- Mostrar clientes demo criados
- Mostrar planos comerciais disponíveis

**Fala:** "Aqui temos a visão central de toda a operação. Saúdade da stack, clientes ativos, uso global."

## 2. Cenário Clínica (5 min)

- Selecionar cliente "Clínica Saúde Total Demo"
- Abrir **Client Portal** (`http://localhost:18080/client-portal`)
- Mostrar: perfil do cliente, plano contratado, limites
- Fazer uma pergunta no playground (chat)
- Mostrar que está rodando local (desligar Wi-Fi e mostrar que funciona)

**Fala:** "Note que mesmo sem internet o sistema responde. Seus dados de pacientes nunca saem daqui."

## 3. RAG - Base de Conhecimento (5 min)

- Demonstrar upload de documento fictício via API
- Fazer query RAG sobre o documento
- Mostrar retrieval + geração combinados

**Fala:** "O RAG permite que o modelo busque nos seus documentos antes de responder. Isso reduz alucinações e garante respotas baseadas em fatos."

## 4. Admin Lab - Gestão (3 min)

- Acessar **Admin Lab** (`http://localhost:18080/admin-lab`)
- Mostrar aba de faturamento com invoices geradas
- Mostrar planos e limites configuráveis
- Mostrar API keys criadas

**Fala:** "Aqui o provedor controla tudo: planos, clientes, faturas. O billing é local/manual sem precisar de gateway de pagamento."

## 5. Provedor de API (5 min)

- Criar novo cliente via API Admin
- Gerar API key
- Testar endpoint OpenAI-compatible
- Mostrar rate limiting em ação

**Fala:** "API 100% compatível com OpenAI. Seu cliente muda a URL e começa a usar. Mesmo SDK, mesma API."

## 6. Múltiplas Capacidades (3 min)

- Demonstrar TTS (se habilitado)
- Demonstrar embeddings
- Mostrar responses

**Fala:** "Não é só chat. A stack inclui voz, busca semântica e respostas estruturadas."

## Fechamento (5 min)

- Mostrar pricing dos planos
- Mostrar documentação e checklist pré-cliente
- Responder objeções

**Fala:** "Instalação em 15 minutos. Dados 100% locais. Suporte incluso. Posso agendar um teste pilot esta semana."

## Recursos Visuais

Durante a demo, tenha abertos:
1. **Admin Dashboard** - métricas e saúde
2. **Client Portal** - experiência do cliente final
3. **Admin Lab** - gestão e faturamento
4. **Terminal** - requisições curl
5. **Landing Page** - posicionamento do produto
