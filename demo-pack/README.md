# Demo Pack Comercial - llm-inference-stack

Pacote de demonstração comercial para apresentar o sistema a clientes sem configurar dados, roteiro e fluxos manualmente.

> **ATENÇÃO:** Sempre use `make reset-demo-pack` (dry-run) antes de reuniões com clientes
> para garantir que dados de demonstração anteriores não interfiram na apresentação.
> O reset seguro usa `metadata demo=true` e NUNCA afeta dados reais.

## Conteúdo

| Arquivo | Descrição |
|---------|-----------|
| `demo-scenarios.json` | 5 cenários comerciais fictícios com problema, demonstração, endpoints e valor comercial |
| `demo-clients.json` | 5 clientes fictícios com planos, limites e configurações |
| `demo-documents/` | Documentos RAG fictícios por cenário (legado) |
| `demo-prompts.md` | Prompts sugeridos para cada cenário |
| `demo-api-requests.md` | Requisições curl para demonstrar cada endpoint |
| `demo-objection-handling.md` | Objeções comuns e respostas sugeridas |
| `demo-flow.md` | Roteiro da demonstração passo a passo |
| `fake-data/` | **Fonte oficial de dados fictícios** para seed, validação e testes |

## Comandos Rápidos

```bash
# Carregar dados demo no sistema
make demo-pack

# Validar que o demo pack está íntegro
make validate-demo-pack

# Reset seguro (dry-run por padrão - não apaga nada)
make reset-demo-pack

# Reset real (requer --yes)
./scripts/reset-commercial-demo-pack.sh --yes

# Validar segurança do reset
make validate-reset-demo-pack

# Executar testes do demo pack
.venv/bin/python -m pytest tests/test_commercial_demo_pack.py tests/test_commercial_demo_seed.py tests/test_commercial_demo_security.py -q

# Executar testes de segurança do reset
.venv/bin/python -m pytest tests/test_reset_commercial_demo_pack.py tests/test_reset_demo_safety.py -q
```

## Cenários

1. **Clínica Local** - Dados sensíveis de pacientes, compliance LGPD
2. **Escritório Jurídico** - Contratos, jurisprudência, pareceres
3. **Suporte Técnico** - Knowledge base, tickets, respostas automáticas
4. **Escola/Treinamento** - Material didático, correção, tutoria
5. **Provedor de API de IA** - Marketplace de modelos, API para terceiros

## Dados Fictícios (fake-data)

O diretório `fake-data/` é a **fonte oficial** de dados fictícios para o demo pack.

| Arquivo | Descrição |
|---------|-----------|
| `clients.json` | 5 clientes fictícios com IDs determinísticos, e-mails `*.demo.local` |
| `plans.json` | 5 planos comerciais fictícios com limites e preços |
| `invoices.json` | 5 faturas fictícias no valor do plano |
| `usage.json` | Uso mensal simulado por cliente |
| `tts_samples.json` | 5 textos TTS fictícios por cenário |
| `prompts.json` | 10 prompts de teste por cenário/categoria |
| `rag_documents/` | 5 documentos RAG fictícios com marcador DEMO |

**Garantias:** Nenhum CPF/CNPJ real, nenhum e-mail fora de `demo.local`,
nenhum telefone real (prefixo `99999`), nenhum secret, nenhum dado sem
marcação `demo=true` ou `DEMO/FICTICIO`.

Validacão: `make validate-fake-data`

## Aviso

> **Todos os dados são fictícios e criados exclusivamente para demonstração.**
> Nenhum cliente real, dado real ou chave de produção é utilizado.
> `demo=true` em todos os metadados.
