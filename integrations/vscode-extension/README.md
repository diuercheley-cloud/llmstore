# LLM Inference Stack - VS Code Extension

Esta extensão integra o VS Code localmente com a sua instância do `llm-inference-stack`.

## Funcionalidades

- **LLM Stack: Connect**: Salva sua API Key de forma segura usando o `SecretStorage` do VS Code.
- **LLM Stack: Run Workflow**: Executa o workflow definido no arquivo YAML aberto no editor diretamente na stack local.
- **LLM Stack: Explain Selection**: Abre o chat do agente com o texto selecionado pronto para ser explicado.
- **Agent Chat**: Webview lateral para conversar com seus agentes.

## Configuração

- `llmStack.apiBaseUrl`: URL da API do Control Plane (Default: `http://localhost:8000`).
- `llmStack.defaultAgent`: ID do agente padrão para interações.

## Como Desenvolver e Rodar Localmente

1. Entre no diretório: `cd integrations/vscode-extension`
2. Instale as dependências: `npm install`
3. Compile o código: `npm run compile`
4. Pressione `F5` no VS Code para abrir uma nova janela com a extensão carregada.

## Segurança

- As chaves de API nunca são salvas em arquivos de texto plano ou `settings.json`.
- Logs da extensão ocultam automaticamente padrões sensíveis.

## Checklist para Publicação Futura

- [ ] Implementar chamadas reais de API usando `axios` ou `node-fetch`.
- [ ] Adicionar ícones oficiais da stack.
- [ ] Implementar suporte completo a Streaming no Webview de Chat.
- [ ] Adicionar testes de integração usando `@vscode/test-electron`.
- [ ] Configurar workflow de CI/CD para gerar o arquivo `.vsix`.
- [ ] Revisar políticas de privacidade e segurança.
