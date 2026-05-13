# Sales - LLM Inference Stack

## Enterprise RAG — Casos de Uso

### Jurídico
- Upload de contratos (.pdf, .docx)
- Consulta sobre cláusulas e obrigações
- Citações com fonte e página

### Suporte
- Upload de FAQs e manuais (.txt, .md, .pdf)
- Respostas baseadas em documentação interna
- Isolamento total por cliente

### RH
- Upload de políticas internas (.docx, .xlsx)
- Consulta sobre benefícios e regras
- Segurança: dados sensíveis nunca vão para cloud

### Vendas
- Upload de propostas e catálogos (.pdf, .xlsx)
- Consulta sobre preços e condições
- Embeddings locais garantem confidencialidade

### Imobiliária
- Upload de contratos e fichas de imóveis (.pdf, .csv)
- Consulta sobre metragens, valores e regras

## Formatos Suportados

| Formato | Sempre | Com dependência |
|---------|--------|-----------------|
| .txt    | ✓      |                 |
| .md     | ✓      |                 |
| .csv    | ✓      |                 |
| .pdf    |        | pymupdf         |
| .docx   |        | python-docx     |
| .xlsx   |        | openpyxl        |

## Políticas Comerciais

- Planos Free/Basic: ativado via feature
- Planos Pro/Enterprise: completo com coleções
- Cloud embeddings: apenas se tenant explicitamente permite
- Storage limits por plano

## Diferenciais

1. **Zero cloud dependency** — Tudo roda local
2. **LGPD-ready** — Dados nunca saem do appliance
3. **Multi-formato** — PDF, DOCX, XLSX, CSV, TXT, MD
4. **Multi-tenant** — Isolamento completo entre clientes
5. **Sem lock-in** — Embeddings locais ou qualquer provider

## Custos por Provider (v1.8.1)

A plataforma agora mede custos reais por provider cloud (OpenAI, DeepSeek, Anthropic)
para embasar propostas comerciais com dados reais de margem.

### Como gerar relatório de custos

```bash
# Dry-run (sem chamadas reais)
make measure-provider-costs-dry

# Com chamadas reais mínimas
make measure-provider-costs
```

### Relatório gerado

O relatório em `artifacts/real-provider-validation/costs/<timestamp>/provider-costs.md`
contém por provider:

| Campo | Descrição |
|-------|-----------|
| Provider Cost USD | Custo real/estimado do provider |
| Provider Cost BRL | Convertido para BRL |
| Customer Price BRL | Preço que seria cobrado (plano Pro) |
| Gross Profit BRL | Lucro bruto por request |
| Margin % | Margem percentual |

### Exemplo de saída

```
| openai | PASS | gpt-4o-mini | 100 | 50 | 150 | 1200 | 0.00004500 | 0.00022500 | 0.00400000 | 0.00377500 | 94.38% |
```

### Endpoint Admin

```bash
curl -H "X-Admin-Token: $ADMIN_TOKEN" \
  http://localhost:8080/admin/providers/cost-validation/latest
```

Retorna o último relatório sanitizado (chaves mascaradas, sem prompts).

### Uso em Propostas

Os dados de custo real ajudam a:

- Calcular markup realista por provider
- Demonstrar transparência de custos para o cliente
- Validar que a margem da plataforma é sustentável
- Comparar custo entre providers para recomendar o mais econômico

## Validation
Sales margins can be validated using the real provider cost validation script.
