---
owner: platform-ops
status: consolidated
---

# Objeções Comuns e Respostas — Demonstração Comercial

> **Uso:** Este documento ajuda o time de vendas a responder objeções com confiança e transparência.
> **Aviso:** Todos os dados da demonstração são fictícios. Esta demonstração utiliza dados fictícios — nenhuma informação real. O sistema é appliance local — dados não saem da sua rede.
> Billing é manual/local — sem PSP/PIX real.
> Lembre-se: não prometa PSP/PIX real, cloud gerenciada, segurança absoluta, nem substituição de análise jurídica.

---

## Objeção 1: "Por que não usar OpenAI direto?"

**Contexto:** Cliente já usa OpenAI API e questiona por que adotar um appliance local.

**Resposta:**

"Ótima pergunta. A OpenAI é excelente para muitos casos, mas há cenários onde o appliance local é mais adequado:

1. **Dados sensíveis:** Se sua empresa lida com LGPD, dados de saúde (LGPD + CFM), sigilo advocatício ou informações financeiras, enviar prompts para uma API pública pode violar compliance. Com o appliance local, **nenhum dado sai da sua rede**.

2. **Custos previsíveis:** Na OpenAI, o custo é por token e pode escalar rapidamente sem controle granular por departamento. Aqui você define planos, cotas e faturamento por cliente — o custo mensal é previsível.

3. **Latência consistente:** APIs públicas têm latência variável conforme carga global. O appliance local oferece latência consistente.

4. **Disponibilidade total:** Você não depende de internet ou de downtime de terceiros.

5. **Modelos customizáveis:** Você escolhe o modelo GGUF que melhor atende seu caso — não fica preso ao catálogo de um fornecedor.

**Resumo:** Para uso pessoal ou dados não sensíveis, OpenAI é prática. Para dados regulados, controle de custo e soberania, o appliance local é a escolha certa."

---

## Objeção 2: "E se o modelo local for pior que GPT-4/Gemini/Claude?"

**Contexto:** Cliente preocupado com qualidade inferior dos modelos locais.

**Resposta:**

"Modelos locais como Gemma 4, Llama 3 e Mistral evoluíram muito. Para **80% dos casos de uso empresariais** — suporte ao cliente, análise de documentos, RAG sobre knowledge base interna, assistentes de produtividade — eles performam tão bem quanto modelos maiores da nuvem.

**Onde modelos locais são excelentes:**
- RAG sobre documentos internos (o modelo busca no seu conteúdo)
- Tarefas estruturadas (classificação, extração, resumo)
- Chatbots de suporte com base em knowledge base
- Assistentes internos com escopo definido

**Onde modelos cloud ainda lideram:**
- Criatividade geral irrestrita
- Raciocínio multi-etapa extremamente complexo
- Conhecimento enciclopédico atualizado (se você não usar RAG)

**Nossa recomendação:** Faça uma prova de conceito com seus dados reais (não sensíveis) e compare. Na maioria dos casos, o modelo local atende ou supera as expectativas — com a vantagem da privacidade total. E lembrando: você pode trocar o modelo a qualquer momento pela UI do Admin Lab, sem precisar de nova instalação."

---

## Objeção 3: "Isso é seguro?"

**Contexto:** Cliente questiona segurança do appliance.

**Resposta:**

"Segurança é uma preocupação legítima. Vou ser transparente:

**O que o sistema faz para segurança:**
- Toda inferência, armazenamento e indexação RAG são **100% locais** — dados nunca saem da sua rede
- API keys armazenadas com hash bcrypt — nem o admin recupera a chave original
- Isolamento multi-tenant — cada cliente com índice RAG, cotas e chaves próprias
- Rate limiting e bloqueio automático por cliente
- Relatórios de readiness e security scan
- Sem telemetria externa

**O que não prometemos:**
- **Não garantimos segurança absoluta** — nenhum sistema está 100% seguro
- **Não substituímos análise de compliance** — recomendamos que seu time de segurança avalie o appliance
- **Não substituímos firewalls, WAF ou outras camadas de rede** — o appliance é um componente dentro da sua arquitetura de segurança

**Nossa sugestão:** Baixe o security report (`./scripts/validators/security-report-local.sh`), compartilhe com seu time de segurança e agende uma call técnica para esclarecer dúvidas específicas do seu ambiente."

---

## Objeção 4: "Quem dá suporte se algo falhar?"

**Contexto:** Cliente preocupado com suporte técnico.

**Resposta:**

"O suporte varia conforme o plano contratado:

| Plano | Suporte Incluso |
|-------|-----------------|
| Free | Comunitário (issues GitHub, documentação) |
| Basic | E-mail em até 48h úteis |
| Pro | E-mail prioritário em até 24h úteis |
| Enterprise Local | 24/7 dedicado com SLA contratual |

Além disso:
- Documentação completa em `docs/` (instalação, troubleshooting, runbook)
- Scripts de diagnóstico (`./scripts/dev/diagnose-readiness-warnings-local.sh`)
- Relatórios de health e readiness
- Backup e restore documentados
- Upgrade e rollback com script validado

**Para Enterprise Local,** oferecemos instalação assistida, treinamento da equipe e canais diretos com engenharia."

---

## Objeção 5: "Quanto custa?"

**Contexto:** Cliente quer saber preço.

**Resposta:**

"O custo do appliance local tem dois componentes:

**1. Licenciamento do software (planos mensais):**

| Plano | Tokens/mês | RPM/RPD | RAG | TTS | Preço estimado* |
|-------|-----------|---------|-----|-----|-----------------|
| Free | 50.000 | 10/100 | Não | Não | Grátis |
| Basic | 500.000 | 30/1.000 | 5 docs | Sim | R$ 197/mês |
| Pro | 5.000.000 | 60/5.000 | 50 docs | Sim | R$ 997/mês |
| Enterprise Local | 50.000.000 | 300/1M | 1.000 docs | Sim | Sob consulta |

> *Preços estimados. Consulte proposta comercial para valores vigentes.

**2. Hardware (investimento único do cliente):**

O appliance roda no hardware que você já tem ou em servidor dedicado:
- **Mínimo:** 16 GB RAM, CPU 8 cores, SSD 100 GB (CPU-only)
- **Recomendado:** GPU NVIDIA 12 GB+ VRAM, 32 GB RAM, SSD 500 GB

**Comparativo:** Uma prova de conceito com dados reais (não sensíveis) ajuda a dimensionar o plano ideal sem compromisso inicial.

**Lembrando:** O faturamento é manual/local — sem PSP/PIX real integrado."

---

## Objeção 6: "Dá para integrar com sistemas internos?"

**Contexto:** Cliente quer saber se pode conectar ERP, CRM, sistemas legados.

**Resposta:**

"Sim, a integração é via API REST OpenAI-compatible exposta em `http://localhost:18080/v1`. Como é 100% compatível com OpenAI:

- **Qualquer linguagem:** Python, Node.js, Java, Go, C# — qualquer cliente HTTP
- **Ferramentas compatíveis:** LangChain, LlamaIndex, Open WebUI, n8n, AnythingLLM, Flowise
- **Automação:** n8n e Make (Integromat) conectam via nó OpenAI
- **Sistemas internos:** Basta apontar para a URL base do appliance

**Exemplo de integração com sistema interno em Python:**
```python
import requests

response = requests.post(
    "http://localhost:18080/v1/chat/completions",
    headers={
        "Authorization": "Bearer sk-demo-xxxx",
        "Content-Type": "application/json"
    },
    json={
        "model": "unsloth/gemma-4-E4B-it-GGUF",
        "messages": [{"role": "user", "content": "Resuma este relatório"}],
        "max_tokens": 512
    }
)
```

**Não oferecemos cloud gerenciada — tudo é on-premise."

**URLs de referência para integração:**
- API: `http://localhost:18080/v1`
- Admin Dashboard: `http://localhost:18080/admin-dashboard`
- Admin Lab: `http://localhost:18080/admin-lab`
- Client Portal: `http://localhost:18080/client-portal`**

---

## Objeção 7: "E LGPD?"

**Contexto:** Cliente preocupado com adequação à Lei Geral de Proteção de Dados.

**Resposta:**

"O appliance local foi projetado para ajudar na adequação à LGPD, mas **não substitui análise jurídica nem garante compliance automaticamente**:

**Como o appliance ajuda:**
- **Art. 46 (Medidas de segurança):** Dados processados localmente, sem transferência para terceiros
- **Art. 18 (Direitos do titular):** Sistema suporta exportação e exclusão de dados de clientes/tenants
- **Art. 49 (Suspensão de tratamento):** Bloqueio e suspensão por inadimplência ou solicitação
- **Relatórios de segurança:** Evidências para auditoria e DPO
- **Registro de operações:** Logs de acesso e uso disponíveis

**O que você precisa fazer por conta própria:**
- Nomear DPO (Encarregado de Dados)
- Realizar ROPA (Registro de Operações de Tratamento)
- Avaliar necessidade de RIA (Relatório de Impacto)
- Contratar seguro de responsabilidade civil (se aplicável)
- Obter consentimento dos titulares conforme sua base legal

**Recomendação:** Consulte seu departamento jurídico ou DPO. O appliance fornece as ferramentas técnicas — a adequação formal depende do seu programa de governança."

---

## Objeção 8: "E se a GPU falhar?"

**Contexto:** Cliente preocupado com disponibilidade caso hardware falhe.

**Resposta:**

"Planejamos para isso:

1. **Fallback para CPU:** Se a GPU falhar, o sistema automaticamente tenta continuar operando em CPU apenas — mais lento, mas não para completamente.

2. **Health monitoring:** O Admin Dashboard e os endpoints `/health` e `/ready` detectam falhas de GPU imediatamente.

3. **Backup e restore:** Scripts prontos para recuperação completa em outro hardware.

4. **Recomendação Enterprise:** Para clientes que não podem tolerar downtime, recomendamos:
   - Duas GPUs em servidores diferentes (active/passive)
   - Backup diário automatizado
   - Contrato de suporte Enterprise Local com SLA

**Resumo:** A falha de GPU degrada a performance (fallback CPU), mas não para o sistema. Para alta disponibilidade, planejamos redundância de hardware."

---

## Objeção 9: "Como escalar?"

**Contexto:** Cliente preocupado se o sistema acompanha o crescimento.

**Resposta:**

"O appliance escala de duas formas:

**1. Escala vertical (mesmo servidor):**
- GPU mais potente (mais VRAM = mais tokens, maior contexto)
- Mais RAM e CPU
- SSD mais rápido

**2. Escala horizontal (múltiplos servidores):**
- Múltiplos data planes registrados em um control plane
- Roteamento entre backends (LM Studio, Ollama, llama.cpp remoto)
- Cada data plane pode rodar um modelo diferente

**Passos práticos para escalar:**
```
1. Adicionar segundo servidor com GPU
2. Configurar como backend no Admin Lab
3. Control plane roteia requests entre os backends
4. Clientes continuam usando a mesma API key e URL
```

**Importante:** A arquitetura atual funciona melhor com escala vertical. Escala horizontal com múltiplos data planes está disponível mas requer configuração adicional. Não oferecemos cloud gerenciada."

---

## Objeção 10: "Preciso de um contrato de manutenção?"

**Contexto:** Cliente quer saber sobre suporte contínuo.

**Resposta:**

"Recomendamos contrato de suporte para clientes em produção. Opções:

| Nível | Inclui | Ideal para |
|-------|--------|------------|
| Basic | E-mail 48h, atualizações de versão | Equipes com capacidade técnica interna |
| Pro | E-mail 24h, prioridade em bugs, instalação assistida | Empresas com time de TI enxuto |
| Enterprise | 24/7, SLA, treinamento, engenharia dedicada | Grandes operações, missão crítica |

**Sem contrato:** Você ainda tem acesso à documentação, scripts e community support — mas sem garantia de SLA.

**Nota:** Atualizações de segurança e correções críticas são disponibilizadas gratuitamente para todos os clientes com plano ativo."
