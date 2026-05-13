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
