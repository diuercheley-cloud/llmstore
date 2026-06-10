#!/usr/bin/env bash
set -euo pipefail

# Configuração do LM Studio (conforme informado pelo usuário)
BASE_URL="http://192.168.101.1:1234/v1"
MODEL="nvidia/nemotron-3-nano-4b"

# Regras de Memória do Projeto (MEMORY.md)
# - Bypass Cache: "cache_prompt": false
# - Stateless Instruction: Prepend "[Reset Context: New Task]"
# - Sampling Params: temperature: 0.7, min_p: 0.05

echo "Enviando requisição para LM Studio em ${BASE_URL}..."
echo "Modelo: ${MODEL}"

curl -fsS "${BASE_URL}/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{
    \"model\": \"${MODEL}\",
    \"messages\": [
      {
        \"role\": \"user\", 
        \"content\": \"[Reset Context: New Task] Olá! Se você estiver me ouvindo, responda com uma frase curta confirmando que o modelo ${MODEL} está operacional.\"
      }
    ],
    \"temperature\": 0.7,
    \"min_p\": 0.05,
    \"cache_prompt\": false,
    \"max_tokens\": 100,
    \"stream\": false
  }" | python3 -m json.tool
