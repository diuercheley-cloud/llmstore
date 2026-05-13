# Guia de Instalação (Cliente Final)

Bem-vindo ao guia de instalação do LLM Inference Stack. Este guia foi projetado para ajudá-lo a implantar o sistema no seu próprio ambiente de forma simples e direta, operando em `LOCAL_APPLIANCE_MODE` (Modo Appliance Local).

**Aviso Legal:** Esta instalação utiliza simulações para fluxos de faturamento. **Não há promessa de PSP/PIX real** na versão isolada.

## 1. Visão Geral
O sistema será instalado via contêineres Docker, rodando em sua máquina local ou servidor dedicado. Todo o processamento dos dados permanece interno, garantindo privacidade e controle total.

## 2. Baixar o Projeto
Faça o download do pacote fornecido pela nossa equipe de vendas ou clone o repositório em seu servidor de destino:
```bash
# Exemplo se via git (se fornecido acesso)
git clone <url-do-repositorio> llm-inference-stack
cd llm-inference-stack
```

## 3. Preparar a Pasta de Modelos
Crie e organize seus modelos (em formato GGUF) no diretório `models/` na raiz do projeto. O sistema procurará modelos de inferência neste local.

## 4. Rodar o Instalador
Inicie o processo de instalação base usando o script automatizado:
```bash
./scripts/install-local-appliance.sh
```
*(Nota: não execute comandos ou edite arquivos críticos sem orientação de nosso suporte técnico. Nunca compartilhe ou coloque senhas/secrets em fóruns ou chats de suporte não autenticados).*

## 5. Rodar o Assistente de Configuração
Se desejar personalizar portas, caminhos ou configurações iniciais, você pode rodar o assistente interativo (wizard):
```bash
./scripts/configure-local-wizard.sh
```

## 6. Acessar as URLs do Sistema
Assim que a inicialização concluir, acesse as seguintes interfaces pelo seu navegador:
- **Painel Administrativo:** `http://localhost:18080/admin` (ou o IP do servidor)
- **Portal de Inferência:** `http://localhost:18080/portal`

## 7. Criar um Cliente de Demonstração
Para verificar se tudo está funcionando, crie seu primeiro cliente para testar os serviços:
```bash
./scripts/create-customer-demo.sh
```

## 8. Validar o Sistema
Certifique-se de que os componentes estão ativos e saudáveis e realize a validação final pós-instalação:
```bash
make health
make validate
make validate-post-install
```

### Validacao de Instalacao Limpa (para operadores)
Para simular uma instalacao do zero em ambiente isolado (sandbox), sem afetar o repositorio real:
```bash
# Dry-run (seguro, nao altera nada)
./scripts/validate-clean-install-local.sh --dry-run

# Validacao completa (cria sandbox, executa instalador e validacoes)
./scripts/validate-clean-install-local.sh --yes

# Validar os resultados
./scripts/validate-clean-install-validator.sh
```

## 9. Fresh Machine Validation (para operadores)

Antes de instalar em uma máquina nova, utilize o validador de readiness:

```bash
# Verificar pré-requisitos da máquina
./scripts/fresh-machine-readiness-check.sh --dry-run

# Com relatório JSON
./scripts/fresh-machine-readiness-check.sh --dry-run --json
```

Consulte o roteiro completo em [docs/FRESH_MACHINE_VALIDATION.md](FRESH_MACHINE_VALIDATION.md).

## 10. Backup Inicial
Logo após a instalação e validação, crie o seu primeiro ponto de restauração seguro:
```bash
./scripts/backup-local.sh
```

## 11. Atualização Futura
Para atualizar quando recebermos novas versões (via pacote ou repositório), você executará um script de `rollback/upgrade` seguro, garantindo que a versão dos dados seja compatível. O upgrade automaticamente realiza um backup preventivo obrigatório; para pular este passo, o operador deve confirmar os riscos explicitamente (ex. `--skip-backup --yes`). Siga as instruções do pacote de liberação entregue na época.

## 12. White-Label / Branding Personalizado

É possível personalizar a identidade visual do sistema (nome do produto, cores, textos) sem alterar código. Consulte `docs/WHITE_LABEL_LOCAL.md` para instruções.

## 13. Termos Contratuais

Templates de contrato e SOW para referência estão disponíveis no diretório `contracts/`. Esses templates:

- São fornecidos apenas para pré-alinhamento comercial.
- **Não substituem assessoria jurídica.**
- **Não constituem aconselhamento jurídico.**
- **Não prometem garantias absolutas de funcionamento ou compliance.**
- **Não incluem processamento de pagamentos reais (PSP/PIX).**

Consulte `contracts/README.md` para detalhes sobre cada template.

## 12. Checklist de Implantação Paga

Para implantações comerciais com prestação de serviços, utilize o **Paid Implementation Checklist** disponível em `docs/PAID_IMPLEMENTATION_CHECKLIST.md`. Este checklist:

- Separa responsabilidades entre cliente e fornecedor.
- Abrange hardware, instalação, configuração, modelos, segurança, testes de aceite e treinamento.
- Inclui campos para assinatura e aceite formal.
- **Não inclui processamento de pagamentos reais (PSP/PIX).**

```bash
# Gerar checklist personalizado para o cliente
./scripts/paid-implementation-checklist-local.sh --company-name "Cliente" --operator-name "Fornecedor"
```

## 14. Desinstalação Segura
Caso precise remover todo o sistema, os contêineres e redes podem ser removidos. Seus dados no disco (`models/`, bancos de dados mapeados) permanecerão, a menos que deletados manualmente. Use o docker-compose para parar:
```bash
docker compose down -v
```