# Local AI Appliance

> **Appliance local de LLM-as-a-Service | API OpenAI-compatible | RAG | TTS**
> Billing local/manual — sem PSP/PIX real. Dados fictícios em demonstração.

---

## Proposta de Valor

Implante IA generativa **dentro da sua infraestrutura** com API 100% compatível com OpenAI. Sem enviar dados para nuvem. Sem custos imprevisíveis. Sem retrabalho de integração.

---

## Principais Recursos

| Recurso | Descrição |
|---------|-----------|
| **API OpenAI-compatible** | Drop-in replacement. SDKs, LangChain, Open WebUI, n8n funcionam sem alterações |
| **RAG nativo** | Indexe documentos internos. Responda com base no conhecimento da empresa |
| **TTS local** | Síntese de voz on-premise. Sem Google Cloud TTS ou Azure Speech |
| **Portal do Cliente** | Autoatendimento: consumo, chaves, faturas. Isolamento multi-tenant |
| **Admin Dashboard** | Monitoria completa: serviços, uso, latência, erros. Tudo local |
| **Billing manual** | Planos com cotas. Faturamento local/manual — sem PSP/PIX |
| **Security Reports** | Relatórios de readiness e varredura de segurança |

---

## Para Quem Serve

- **Empresas reguladas** (saúde, direito, finanças) que não podem enviar dados a APIs públicas
- **Departamentos de TI** que querem oferecer IA interna com controle de custos
- **Provedores de API** que revendem capacidade de IA como serviço white-label
- **Instituições de ensino e pesquisa** que precisam de IA local sem dependência cloud

---

## Requisitos

| Item | Mínimo | Recomendado |
|------|--------|-------------|
| CPU | 8 cores | 8+ cores |
| RAM | 16 GB | 32 GB |
| GPU | — (CPU) | NVIDIA RTX 3060+ (12 GB VRAM) |
| Armazenamento | 100 GB SSD | 500 GB NVMe |
| Docker | 24+ | 24+ |
| SO | Linux ou Windows WSL2 | Linux (Ubuntu 22.04+) |

---

## Como Demonstrar

```bash
make install-local        # Instala com dados demo fictícios
make demo-pack            # Carrega cenários de demonstração
./scripts/validate-e2e.sh # Valida funcionamento
```

Acesse as interfaces:
- Admin Dashboard: `http://localhost:18080/admin-dashboard`
- Client Portal: `http://localhost:18080/client-portal`
- API: `http://localhost:18080/v1`

---

## Limitações

- Modelos locais têm capacidade inferior a GPT-4/Claude em tarefas complexas
- Billing é manual — **sem PSP/PIX real integrado**
- Escala vertical (GPU melhor) é mais simples que escala horizontal
- **Não garantimos segurança absoluta** — consulte seu time de segurança
- **Não substituímos análise de compliance** (LGPD, etc.)
- **Não oferecemos cloud gerenciada** — tudo on-premise

---

*llm-inference-stack — [docs](https://github.com/anomalyco/llm-inference-stack) | Proposta comercial em anexo*
