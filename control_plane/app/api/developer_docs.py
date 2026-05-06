from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

docs_markdown = """
# Developer Documentation (API)

## Introdução
Bem-vindo à documentação da API do LLM Inference Stack. Esta API oferece uma interface compatível com OpenAI para consumo de modelos de linguagem (Control Plane -> Data Plane).

## Base URL Local
A base URL local para todas as requisições é:
`http://localhost:8000`

## Autenticação
Todas as requisições (exceto onboarding) requerem autenticação via cabeçalho `Authorization` com uma API key válida.
Formato: `Authorization: Bearer <sua_api_key>`

---

## Endpoints Principais

### GET /v1/models
Retorna a lista de modelos disponíveis no momento, incluindo detalhes de permissões e disponibilidade no seu plano.

**Exemplo cURL:**
```bash
curl http://localhost:8000/v1/models \\
  -H "Authorization: Bearer <sua_api_key>"
```

### POST /v1/chat/completions
Gera uma resposta baseada no histórico de mensagens fornecido usando o modelo especificado.

**Exemplo cURL:**
```bash
curl -X POST http://localhost:8000/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer <sua_api_key>" \\
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "Olá, como você está?"}],
    "temperature": 0.7
  }'
```

### Streaming
Para receber a resposta em tempo real (Server-Sent Events), defina `"stream": true` no corpo da requisição.

**Exemplo cURL (Streaming):**
```bash
curl -N -X POST http://localhost:8000/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer <sua_api_key>" \\
  -d '{
    "model": "llama3",
    "messages": [{"role": "user", "content": "Escreva um poema curto."}],
    "stream": true
  }'
```

---

## Exemplos de Código

### Python (usando `openai` ou `requests`)
```python
import requests

url = "http://localhost:8000/v1/chat/completions"
headers = {
    "Authorization": "Bearer <sua_api_key>",
    "Content-Type": "application/json"
}
data = {
    "model": "llama3",
    "messages": [{"role": "user", "content": "Olá em Python!"}]
}

response = requests.post(url, headers=headers, json=data)
print(response.json())
```

### Node.js (usando `fetch`)
```javascript
const response = await fetch("http://localhost:8000/v1/chat/completions", {
  method: "POST",
  headers: {
    "Authorization": "Bearer <sua_api_key>",
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    model: "llama3",
    messages: [{ role: "user", content: "Olá em Node.js!" }]
  })
});
const data = await response.json();
console.log(data);
```

---

## Erros Comuns
- `401 Unauthorized`: API key ausente, inválida ou revogada.
- `402 Payment Required`: Cliente suspenso por falta de pagamento.
- `403 Forbidden`: Plano do cliente não tem acesso ao modelo solicitado ou limite atingido.
- `429 Too Many Requests`: Rate limit excedido. Reduza a frequência das chamadas.
- `503 Service Unavailable`: Backend (Data Plane) indisponível ou Circuit Breaker ativado.

## Rate Limit
Os rate limits são definidos por plano (RPM - Requests Per Minute). Quando o limite é excedido, a API retorna `429 Too Many Requests`. O cabeçalho da resposta incluirá detalhes sobre o tempo de espera.

## Quotas
Cada plano possui limites de uso (tokens ou requisições). O uso é monitorado. Caso o limite da cota seja atingido, as requisições falharão até a renovação do ciclo de faturamento.

## Billing Local / Manual
O sistema local simula faturamento e suspensão de contas. Você pode usar os endpoints do `/portal` ou scripts em `/scripts` (ex: `scripts/run-billing-cycle.sh`) para gerar faturas e `scripts/mark-invoice-paid.sh` para pagá-las e evitar o erro `402 Payment Required`.

---

## Funcionalidades Adicionais

### RAG (Retrieval-Augmented Generation)
Se configurado, você pode enviar documentos e consultar a API utilizando embeddings e banco vetorial interno.
- **Upload:** `POST /v1/rag/upload` (via multipart/form-data)
- **Consulta:** `POST /v1/chat/completions` (usando o modelo configurado para RAG ou enviando documentos em `messages`).

### LM Studio Backend
O sistema suporta roteamento para instâncias do LM Studio. Certifique-se de configurar a URL do backend LM Studio nas opções do Control Plane. Modelos expostos pelo LM Studio podem ser integrados e listados via `/v1/models` para roteamento transparente.
"""

html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Developer Documentation</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; background: #f9f9f9; }
        .container { background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        h1, h2, h3 { color: #2c3e50; }
        pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; position: relative; }
        code { font-family: Consolas, Monaco, 'Andale Mono', 'Ubuntu Mono', monospace; font-size: 14px; }
        .copy-btn { position: absolute; top: 10px; right: 10px; background: #e0e0e0; border: none; padding: 5px 10px; cursor: pointer; border-radius: 4px; font-size: 12px; }
        .copy-btn:hover { background: #d0d0d0; }
        blockquote { border-left: 4px solid #3498db; padding-left: 15px; color: #666; background: #f0f8ff; padding: 10px; border-radius: 4px; margin-left: 0; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
</head>
<body>
    <div class="container" id="content"></div>
    
    <script>
        const markdownContent = `{{ DOCS_MARKDOWN }}`;
        
        document.getElementById('content').innerHTML = marked.parse(markdownContent);
        
        // Add copy buttons to code blocks
        document.querySelectorAll('pre').forEach((pre) => {
            const button = document.createElement('button');
            button.innerText = 'Copiar';
            button.className = 'copy-btn';
            
            button.addEventListener('click', () => {
                const code = pre.querySelector('code').innerText;
                navigator.clipboard.writeText(code).then(() => {
                    button.innerText = 'Copiado!';
                    setTimeout(() => button.innerText = 'Copiar', 2000);
                });
            });
            
            pre.appendChild(button);
        });
    </script>
</body>
</html>
"""

@router.get("/developer-docs", response_class=HTMLResponse, include_in_schema=False)
async def get_developer_docs():
    # Replace placeholder with markdown (escaping backticks and newlines properly for JS template literal)
    safe_markdown = docs_markdown.replace('`', '\\`').replace('$', '\\$')
    html_content = html_template.replace('{{ DOCS_MARKDOWN }}', safe_markdown)
    return html_content
