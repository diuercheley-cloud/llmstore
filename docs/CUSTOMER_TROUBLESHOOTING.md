---
owner: platform-ops
status: consolidated
---

# Guia de Solução de Problemas (Troubleshooting)

Este guia cobre os problemas mais comuns encontrados por clientes durante ou após a instalação do sistema no modo Appliance Local.

## Códigos de Erro Padronizados
O sistema utiliza um padrão de mensagens amigáveis para facilitar o diagnóstico. Quando um script falha, você verá uma mensagem no formato:

```text
[ERROR] Código: DOCKER_NOT_RUNNING
O que aconteceu:
O Docker não parece estar rodando no sistema.
Como resolver:
Inicie o Docker Desktop ou rode sudo systemctl start docker.
Detalhe técnico:
docker info falhou com exit code 1.
```

Consulte o catálogo completo em [docs/OPERATOR_ERROR_CODES.md](OPERATOR_ERROR_CODES.md).

## 1. Docker não inicia
- **Sintoma:** Comandos `make` ou `docker compose` falham dizendo que o *daemon* não está rodando.
- **Solução:** No Linux, certifique-se de que o serviço Docker está ativo com `sudo systemctl start docker`. No Windows (WSL2), garanta que o Docker Desktop está aberto e rodando.

## 2. Porta 18080 Ocupada
- **Sintoma:** O proxy (Caddy/Nginx) falha ao inicializar informando "bind: address already in use".
- **Solução:** Outro serviço na sua máquina está utilizando a porta 18080. Você pode parar o serviço concorrente ou alterar a porta no assistente de instalação (`./scripts/configure-local-wizard.sh`).

## 3. Modelo não encontrado
- **Sintoma:** As requisições de chat falham com erro de que o modelo especificado não pôde ser carregado.
- **Solução:** Verifique se o arquivo `.gguf` existe na pasta `models/` na raiz da instalação e se o nome requisitado na API bate exatamente com o nome de ativação do modelo.

## 4. GPU não detectada
- **Sintoma:** A inferência é extremamente lenta ou logs indicam `CUDA error`.
- **Solução:** Para suporte a GPU no Docker, instale o `NVIDIA Container Toolkit` na máquina host. No arquivo `docker-compose`, garanta que a seção `deploy.resources.reservations.devices` está habilitada.

## 5. LM Studio Offline (Caso usando servidor externo)
- **Sintoma:** Timeout nas respostas.
- **Solução:** Se você conectou a plataforma a um provedor ou ferramenta local (como LM Studio), garanta que a opção "Start Server" (iniciar servidor) no aplicativo do LM Studio foi ativada.

## 6. /ready degraded
- **Sintoma:** O comando `make health` diz que a API principal não está pronta.
- **Solução:** Inspecione os logs com `docker compose logs control-plane`. Pode ser um erro de permissão no banco de dados, que requer permissões de leitura/escrita corretas na pasta local, ou o banco SQLite demorando para inicializar.

## 7. API key inválida
- **Sintoma:** Erro `401 Unauthorized` ou `403 Forbidden` ao acessar endpoints de inferência.
- **Solução:** Utilize a chave de API gerada durante o `make demo` ou obtenha uma nova através do painel Administrativo. A chave deve ser enviada no header `Authorization: Bearer <sua_chave>`.

## 8. RAG não responde
- **Sintoma:** Consultas em documentos retornam vazias ou dão erro.
- **Solução:** O serviço vetorial ou de embeddings pode estar offline. Verifique se o modelo de embeddings padrão existe e o serviço de dados responde usando `make validate`.

## 9. TTS não gera áudio
- **Sintoma:** Texto não é convertido em voz (Text-to-Speech).
- **Solução:** O módulo `pocket-tts` pode precisar de download inicial dos modelos de voz, o que falhará sem acesso à internet caso não estejam pre-cacheados. Verifique os logs do TTS.

## 10. Security Report Warning
- **Sintoma:** O comando `make security` aponta falhas ou alertas.
- **Solução:** Analise o log do reporte (ex. `scripts/parse-security-report-local.sh`). Alertas de arquivos soltos ou permissões excessivas (ex: `chmod 777`) devem ser corrigidos na máquina host.

## 11. Fresh Machine Validation Failed

- **Sintoma:** `fresh-machine-readiness-check.sh --dry-run` aponta falhas.
- **Solução:** Consulte [FRESH_MACHINE_VALIDATION.md](FRESH_MACHINE_VALIDATION.md) para o checklist completo. Verifique Docker, permissões de script, `.env.local` e disponibilidade de modelo GGUF.

## Como coletar logs
Se o suporte técnico for necessário, colete os logs completos usando:
```bash
docker compose logs --no-color > debug_logs.txt
```
Envie o arquivo `debug_logs.txt` para análise, **removendo senhas ou tokens que possam ter sido impressos no arquivo (não compartilhe secrets)**.