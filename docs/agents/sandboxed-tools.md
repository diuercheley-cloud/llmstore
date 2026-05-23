# Sandboxed and Restricted Tools

O `llm-inference-stack` implementa camadas rigorosas de isolamento para ferramentas de alto risco, como execução de shell, requisições HTTP e leitura de banco de dados. Estas ferramentas operam sob o princípio do menor privilégio e contenção máxima.

## Shell Command Tool (`shell_command_tool`)

### Restrições
- **Allowlist de Comandos**: Apenas comandos aprovados são permitidos (ex: `ls`, `grep`, `cat`, `ps`, `pwd`).
- **Bloqueio de Caminhos Sensíveis**: Tentativas de acessar `.env`, `data/pki`, arquivos de sistema ou pastas de modelos resultam em erro imediato.
- **Execução sem Shell**: Utiliza `asyncio.create_subprocess_exec` com `shell=False` para prevenir injeção de comandos via expansão de variáveis ou concatenação.
- **Contenção de Output**: O output é truncado em 10KB para evitar exaustão de memória e poluição de logs.

## HTTP GET Tool (`http_get_tool`)

### Restrições
- **Bloqueio de Redes Internas**: É terminantemente proibido acessar `localhost`, `127.0.0.1` ou faixas de IP privado (RFC 1918).
- **Proteção de Metadados**: Acesso ao serviço de metadados de nuvem (`169.254.169.254`) é bloqueado.
- **Métodos Permitidos**: Apenas `GET` e `HEAD` são permitidos por padrão para evitar mutações de estado em APIs externas.
- **Sanitização de Headers**: Headers de autenticação ou chaves de API detectados na resposta são removidos antes de serem entregues ao agente.

## Database Read Tool (`database_read_tool`)

### Restrições
- **Strictly Read-Only**: Apenas consultas que começam com `SELECT` são aceitas. Palavras-chave como `INSERT`, `UPDATE`, `DELETE`, `DROP` ou `ALTER` bloqueiam a execução.
- **Allowlist de Tabelas**: O acesso é restrito a tabelas de observabilidade e logs de agentes. Tabelas de credenciais, usuários ou configurações globais são invisíveis.
- **Filtragem de Colunas**: Colunas contendo `api_key`, `secret`, `password` ou `token` são removidas dos resultados automaticamente.
- **Row Limit Mandatório**: Todas as consultas são encapsuladas em uma subquery com `LIMIT` forçado (máximo de 100 linhas).

## Auditoria e Compliance

Cada execução destas ferramentas gera:
1.  **Policy Decision**: Registro da avaliação do `AgentPolicyEngine`.
2.  **Execution Receipt**: Recibo assinado contendo os hashes dos inputs e outputs sanitizados.
3.  **Audit Log**: Entrada detalhada no `agent_timeline_events` para auditoria posterior.
