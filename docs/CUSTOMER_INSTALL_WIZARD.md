---
owner: platform-ops
status: consolidated
---

# Customer Installation Wizard

Este guia descreve como utilizar o instalador profissional para implantação do LLM Inference Stack em clientes.

## Visão Geral

O `scripts/deploy/install-customer.sh` é um assistente interativo que configura a stack de acordo com perfis de produto específicos, garantindo uma instalação padronizada e segura.

## Perfis de Produto

| Perfil | Descrição | Casos de Uso |
| :--- | :--- | :--- |
| **appliance-local** | Local-first, sem dependência de nuvem. | Ambientes seguros, offline ou air-gapped. |
| **hybrid-provider** | Local + Provedores Cloud (OpenAI, Anthropic). | Melhor custo-benefício e redundância. |
| **demo-sales** | Otimizado para demonstrações com dados fakes. | Pré-venda e demos técnicas. |
| **enterprise-rag** | Foco em processamento pesado de documentos. | Gestão de conhecimento e busca semântica. |
| **dev-lab** | Ambiente de desenvolvimento e testes. | Laboratórios internos e validações. |

## Como Instalar

Para iniciar a instalação, escolha um dos targets do Makefile ou execute o script diretamente:

```bash
# Via Makefile (recomendado)
make appliance-local
# ou
make hybrid-provider
```

O assistente irá solicitar:
1. Porta do serviço (ex: 18080)
2. Domínio ou IP local
3. E-mail do administrador
4. Configurações específicas do perfil (ex: API Keys para provedores cloud)
5. Habilitação de funcionalidades (TTS, RAG)

## Validação Final

Após a instalação, é crucial validar se todos os serviços estão operacionais e seguros.

Execute:
```bash
make customer-ready
```

Este comando verifica:
- Endpoints de saúde (`/health`, `/ready`)
- Listagem de modelos e chat completion
- Proteção da área administrativa
- Acessibilidade do portal do cliente
- Status de RAG e TTS
- Integridade de backups e segredos

O resultado final será **CLIENT READY** ou **NOT READY** com os motivos detalhados.

## Segurança

- O arquivo `.env.customer` é gerado com permissões restritas (600).
- O `ADMIN_TOKEN` é gerado aleatoriamente e não deve ser compartilhado.
- Backups de configurações anteriores são salvos em `.local/backups/customer/`.

## Próximos Passos

1. Acesse o Dashboard Admin na URL informada ao final da instalação.
2. Utilize o API Key do cliente inicial criado para testar integrações.
3. Consulte `docs/OPERATIONS.md` para guias de manutenção.
