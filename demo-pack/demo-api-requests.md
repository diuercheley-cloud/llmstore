# Requisições de Demonstração (API)

Todas as requisições usam `DEMO_API_KEY` gerada pelo script de seed.
Substitua `{DEMO_API_KEY}` pela chave real ou use `source .local/demo-clinica.env` após executar o seed.

## 1. Verificar modelos disponíveis

```bash
curl -s http://localhost:18080/v1/models \
  -H "Authorization: Bearer {DEMO_API_KEY}" | jq .
```

## 2. Chat Completion (Clínica)

```bash
curl -s -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer {DEMO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [
      {"role": "system", "content": "Você é um assistente médico auxiliar. Responda com linguagem clara e profissional."},
      {"role": "user", "content": "Resuma os riscos de um paciente diabético com glicemia de 280 mg/dL"}
    ],
    "max_tokens": 200,
    "temperature": 0.3
  }'
```

## 3. Chat Completion (Jurídico)

```bash
curl -s -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer {DEMO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [
      {"role": "system", "content": "Você é um assistente jurídico. Analise contratos com precisão."},
      {"role": "user", "content": "Analise: multa rescisória de 80% do valor remanescente é abusiva? Fundamente com base no Código Civil."}
    ],
    "max_tokens": 300,
    "temperature": 0.2
  }'
```

## 4. RAG Query (Suporte Técnico)

```bash
curl -s -X POST http://localhost:18080/v1/rag/query \
  -H "Authorization: Bearer {DEMO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual o procedimento para configurar VPN no roteador TP-Link Archer C80?"
  }' | jq .
```

## 5. Chat com RAG (Educação)

```bash
curl -s -N http://localhost:18080/v1/chat/completions \
  -H "Authorization: Bearer {DEMO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "messages": [
      {"role": "system", "content": "Você é um tutor de ensino fundamental. Explique de forma simples e didática."},
      {"role": "user", "content": "Explique o que são mudanças climáticas para um aluno do 6º ano."}
    ],
    "max_tokens": 200,
    "temperature": 0.5
  }'
```

## 6. TTS (qualquer cenário com voz)

```bash
curl -s http://localhost:18080/v1/audio/speech \
  -H "Authorization: Bearer {DEMO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "input": "Olá, bem-vindo ao assistente virtual da sua clínica. Como posso ajudar hoje?",
    "voice": "default",
    "response_format": "wav"
  }' -o demo-tts-output.wav
```

## 7. Embeddings (Jurídico / Suporte)

```bash
curl -s -X POST http://localhost:18080/v1/embeddings \
  -H "Authorization: Bearer {DEMO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "input": "Contrato de prestação de serviços advocatícios"
  }' | jq '.data[0].embedding | length'
```

## 8. Responses (se habilitado)

```bash
curl -s -X POST http://localhost:18080/v1/responses \
  -H "Authorization: Bearer {DEMO_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "default",
    "input": "Explique em uma frase o valor da inferência local."
  }' | jq .
```

## 9. Admin API - Listar clientes

```bash
curl -s http://localhost:18080/admin/clients \
  -H "X-Admin-Token: {ADMIN_TOKEN}" | jq '[.[] | {name, id, metadata_json}]'
```

## 10. Admin API - Listar faturas

```bash
curl -s http://localhost:18080/admin/billing/invoices \
  -H "X-Admin-Token: {ADMIN_TOKEN}" | jq '.invoices[:5]'
```

## 11. Portal do Cliente - Ver perfil

```bash
curl -s http://localhost:18080/portal/me \
  -H "Authorization: Bearer {DEMO_API_KEY}" | jq .
```

## 12. Portal do Cliente - Ver uso

```bash
curl -s http://localhost:18080/portal/usage \
  -H "Authorization: Bearer {DEMO_API_KEY}" | jq .
```

## 13. Admin Dashboard - Demo Summary

```bash
curl -s http://localhost:18080/admin/demo/summary \
  -H "X-Admin-Token: {ADMIN_TOKEN}" | jq .
```
