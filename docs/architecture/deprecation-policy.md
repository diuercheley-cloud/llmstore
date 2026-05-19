# Política de Depreciação de Arquitetura

Este documento define o ciclo de vida de componentes no `llm-inference-stack`.

## Níveis de Ciclo de Vida

### 1. Active (Ativo)
Componente recomendado para uso. Segue os padrões atuais de design e segurança.

### 2. Deprecated (Depreciado)
O componente ainda funciona, mas não deve ser usado em novos desenvolvimentos.
- **Header HTTP**: Requisições para endpoints depreciados retornarão o header `X-Deprecated-Endpoint: true`.
- **Logs**: O uso emitirá um warning nos logs administrativos.
- **Documentação**: Marcar como `[DEPRECATED]` e apontar para a alternativa.

### 3. Sunset (Em Descontinuidade)
O componente tem data marcada para remoção. Avisos agressivos serão emitidos.

### 4. Removed (Removido)
O componente foi removido da base de código.

## Processo de Depreciação
1. Identificar duplicação ou obsolescência.
2. Definir e implementar a alternativa moderna.
3. Adicionar o middleware de depreciação ao componente antigo.
4. Atualizar a documentação.
5. Manter por pelo menos uma versão minor completa antes da remoção (ex: depreciado em v1.8, removido em v1.10).

## Componentes Atualmente Depreciados
- `control_plane/app/api/admin.py` -> Use routers modulares em `app/api/commercial_*`.
- `control_plane/app/api/admin_models_runtime.py` -> Use `app/api/commercial_model_lifecycle_admin.py`.
- `control_plane/app/services/admin_model_management.py` -> Use serviços especializados de gerenciamento de modelos.
- Scripts na raiz do repositório -> Use os equivalentes em `scripts/`.
