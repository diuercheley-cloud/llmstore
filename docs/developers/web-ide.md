# Agent Studio Web IDE

O Web IDE fornece um ambiente de desenvolvimento integrado diretamente no browser para criação e edição de agentes, prompts, ferramentas e plugins.

## Recursos

- **File Explorer**: Navegação nos arquivos do workspace do tenant.
- **Code Editor**: Editor de texto com suporte a sintaxe YAML e JSON.
- **Manifest Editors**: Editores especializados para manifestos de agentes e plugins.
- **Restricted Terminal**: Terminal seguro para execução de comandos permitidos (ex: `pytest`).

## Configuração

Habilite o recurso no arquivo `.env`:

```env
WEB_IDE_ENABLED=true
WEB_IDE_WORKSPACES_DIR=./data/ide_workspaces
```

## Workspace por Tenant

Cada tenant possui um workspace isolado no sistema de arquivos do servidor. Os arquivos são armazenados em subdiretórios baseados no `tenant_id`.

## Segurança do Terminal

O terminal é restrito e não permite acesso direto ao shell do host. Apenas uma lista branca de comandos é permitida para garantir a integridade do sistema.

### Comandos Permitidos
- `pytest`: Executar testes unitários.
- `ls`: Listar arquivos.
- `cat`: Visualizar conteúdo de arquivos.

## Validação de Manifestos

O sistema valida automaticamente o formato e os campos obrigatórios (`name`, `version`) ao salvar ou validar manualmente um manifesto.
