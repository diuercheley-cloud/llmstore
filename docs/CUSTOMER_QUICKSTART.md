# Quickstart de Instalação (Cliente Final)

Implante o LLM Inference Stack em menos de 10 minutos usando nossa automação simplificada. Este documento cobre os passos rápidos de instalação.

> **Importante:** Esta versão de instalação local não contempla processamento de pagamentos em produção. Não há integração com PSP/PIX real.

## Passo a Passo (Caminho Curto)

Abra o terminal no servidor Linux ou Windows (WSL2), navegue até a pasta do projeto e execute os seguintes comandos principais:

1. **Instalar o Sistema (Appliance Local):**
   Baixa imagens, prepara pastas e inicia os contêineres Docker básicos.
   ```bash
   make install-local
   ```

2. **Verificar a Saúde dos Componentes:**
   Garante que o banco de dados, API, RAG e Proxy estão em execução.
   ```bash
   make health
   ```

3. **Validar Fluxos Básicos:**
   Realiza um teste completo no sistema para garantir que as rotas estão funcionando corretamente e gera o relatório oficial pós-instalação.
   ```bash
   make validate
   make validate-post-install
   ```

4. **Gerar Dados de Demonstração:**
   Cria um usuário/tenant para que você consiga visualizar as interfaces administrativas e testar chamadas.
   ```bash
   make demo
   ```

5. **Verificar Segurança Base:**
   Analisa se os artefatos locais não contém configurações padrão fáceis de explorar e garante que permissões estão adequadas.
   ```bash
   make security
   ```

## Onde Acessar

Após finalizar o `make demo`, as ferramentas já estarão online no seu IP local ou `localhost`:

- **Admin Dashboard:** `http://localhost:18080/admin`
- **Portal de Usuário/API:** `http://localhost:18080/portal`
- **Documentação Local da API:** `http://localhost:18080/docs`

Se ocorrer qualquer problema, consulte o [CUSTOMER_TROUBLESHOOTING.md](./CUSTOMER_TROUBLESHOOTING.md).

## Instalação Limpa (Sandbox)

Para testar uma instalação do zero sem risco ao sistema atual:

```bash
# Simular instalação limpa (modo dry-run)
./scripts/validate-clean-install-local.sh --dry-run

# Validar o resultado
./scripts/validate-clean-install-validator.sh
```