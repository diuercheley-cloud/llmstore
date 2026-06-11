---
owner: platform-ops
status: reference-generated
generated_from:
  - config/profiles/*.yaml
generated_by: scripts/docs/generate_docs_site.py
---

# Profiles Reference

This page is generated from the official operational profile manifests.

## Summary

| Profile | Description | Enabled Features |
| --- | --- | --- |
| `agentic` | Standard profile extended with memory, tools, workflows, and agents. | agents, inference_proxy, memory, multi_model, observability_basic, postgresql, prometheus, rag_basic, tools, workflows |
| `enterprise` | Full platform profile with enterprise observability, tenancy, federation, and marketplace. | agents, federation, inference_proxy, loki, marketplace, memory, multi_model, multi_tenant, observability_basic, postgresql, prometheus, rag_basic, tempo, tools, workflows |
| `lite` | Local profile with the minimum services required for inference and basic RAG. | inference_proxy, rag_basic, sqlite |
| `standard` | PostgreSQL profile with basic observability and multi-model inference. | inference_proxy, multi_model, observability_basic, postgresql, prometheus, rag_basic |

## `agentic`

Source: `config/profiles/agentic.yaml`

Standard profile extended with memory, tools, workflows, and agents.

### Settings

- `AGENT_CLUSTER_FEDERATION_ENABLED` = `False`
- `AGENT_EXECUTION_ENABLED` = `True`
- `AGENT_MARKETPLACE_ENABLED` = `False`
- `AGENT_MEMORY_ENABLED` = `True`
- `AGENT_MEMORY_SEARCH_ENABLED` = `True`
- `AGENT_REMOTE_MARKETPLACE_ENABLED` = `False`
- `AGENT_RUNTIME_ENABLED` = `True`
- `AGENT_STATEFUL_WORKFLOWS_ENABLED` = `True`
- `AGENT_TOOL_EXECUTION_ENABLED` = `True`
- `AGENT_TOOL_REGISTRY_ENABLED` = `True`
- `COMMERCIAL_FEDERATION_ENABLED` = `False`
- `COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED` = `False`
- `DATABASE_URL` = `postgresql+asyncpg://postgres:postgres@localhost:5432/llm_stack`
- `MULTI_CLUSTER_ENABLED` = `False`
- `OBSERVABILITY_ENABLED` = `True`
- `OPERATIONAL_PROFILE` = `agentic`
- `PLUGIN_MARKETPLACE_ENABLED` = `False`
- `PROVIDERS_ENABLED` = `local,lmstudio,vllm`
- `RAG_ENABLED` = `True`

### Feature Matrix

- `agents`: `enabled`
- `federation`: `disabled`
- `inference_proxy`: `enabled`
- `loki`: `disabled`
- `marketplace`: `disabled`
- `memory`: `enabled`
- `multi_model`: `enabled`
- `multi_tenant`: `disabled`
- `observability_basic`: `enabled`
- `postgresql`: `enabled`
- `prometheus`: `enabled`
- `rag_basic`: `enabled`
- `sqlite`: `disabled`
- `tempo`: `disabled`
- `tools`: `enabled`
- `workflows`: `enabled`


## `enterprise`

Source: `config/profiles/enterprise.yaml`

Full platform profile with enterprise observability, tenancy, federation, and marketplace.

### Settings

- `AGENT_CLUSTER_FEDERATION_ENABLED` = `True`
- `AGENT_EXECUTION_ENABLED` = `True`
- `AGENT_MARKETPLACE_ENABLED` = `True`
- `AGENT_MEMORY_ENABLED` = `True`
- `AGENT_MEMORY_SEARCH_ENABLED` = `True`
- `AGENT_REMOTE_MARKETPLACE_ENABLED` = `True`
- `AGENT_RUNTIME_ENABLED` = `True`
- `AGENT_STATEFUL_WORKFLOWS_ENABLED` = `True`
- `AGENT_TOOL_EXECUTION_ENABLED` = `True`
- `AGENT_TOOL_REGISTRY_ENABLED` = `True`
- `CLOUD_PROVIDERS_ENABLED` = `True`
- `COMMERCIAL_FEDERATION_ENABLED` = `True`
- `COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED` = `True`
- `DATABASE_URL` = `postgresql+asyncpg://postgres:postgres@localhost:5432/llm_stack`
- `DISTRIBUTED_RUNTIME_ENABLED` = `True`
- `MULTI_CLUSTER_ENABLED` = `True`
- `OBSERVABILITY_ENABLED` = `True`
- `OPERATIONAL_PROFILE` = `enterprise`
- `OTLP_EXPORT_ENABLED` = `True`
- `PLUGIN_MARKETPLACE_ENABLED` = `True`
- `PLUGIN_RUNTIME_ENABLED` = `True`
- `PROVIDERS_ENABLED` = `local,lmstudio,vllm,openai,anthropic,deepseek,openrouter`
- `RAG_ENABLED` = `True`

### Feature Matrix

- `agents`: `enabled`
- `federation`: `enabled`
- `inference_proxy`: `enabled`
- `loki`: `enabled`
- `marketplace`: `enabled`
- `memory`: `enabled`
- `multi_model`: `enabled`
- `multi_tenant`: `enabled`
- `observability_basic`: `enabled`
- `postgresql`: `enabled`
- `prometheus`: `enabled`
- `rag_basic`: `enabled`
- `sqlite`: `disabled`
- `tempo`: `enabled`
- `tools`: `enabled`
- `workflows`: `enabled`


## `lite`

Source: `config/profiles/lite.yaml`

Local profile with the minimum services required for inference and basic RAG.

### Settings

- `AGENT_CLUSTER_FEDERATION_ENABLED` = `False`
- `AGENT_MARKETPLACE_ENABLED` = `False`
- `AGENT_MEMORY_ENABLED` = `False`
- `AGENT_REMOTE_MARKETPLACE_ENABLED` = `False`
- `AGENT_RUNTIME_ENABLED` = `False`
- `AGENT_STATEFUL_WORKFLOWS_ENABLED` = `False`
- `AGENT_TOOL_EXECUTION_ENABLED` = `False`
- `AGENT_TOOL_REGISTRY_ENABLED` = `False`
- `CLOUD_PROVIDERS_ENABLED` = `False`
- `COMMERCIAL_FEDERATION_ENABLED` = `False`
- `COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED` = `False`
- `CREATE_TABLES_ON_STARTUP` = `True`
- `DATABASE_URL` = `sqlite+aiosqlite:///./data/lite.db`
- `MULTI_CLUSTER_ENABLED` = `False`
- `OBSERVABILITY_ENABLED` = `False`
- `OPERATIONAL_PROFILE` = `lite`
- `PLUGIN_MARKETPLACE_ENABLED` = `False`
- `PROVIDERS_ENABLED` = `local`
- `RAG_ENABLED` = `True`

### Feature Matrix

- `agents`: `disabled`
- `federation`: `disabled`
- `inference_proxy`: `enabled`
- `loki`: `disabled`
- `marketplace`: `disabled`
- `memory`: `disabled`
- `multi_model`: `disabled`
- `multi_tenant`: `disabled`
- `observability_basic`: `disabled`
- `postgresql`: `disabled`
- `prometheus`: `disabled`
- `rag_basic`: `enabled`
- `sqlite`: `enabled`
- `tempo`: `disabled`
- `tools`: `disabled`
- `workflows`: `disabled`


## `standard`

Source: `config/profiles/standard.yaml`

PostgreSQL profile with basic observability and multi-model inference.

### Settings

- `AGENT_CLUSTER_FEDERATION_ENABLED` = `False`
- `AGENT_MARKETPLACE_ENABLED` = `False`
- `AGENT_MEMORY_ENABLED` = `False`
- `AGENT_REMOTE_MARKETPLACE_ENABLED` = `False`
- `AGENT_RUNTIME_ENABLED` = `False`
- `AGENT_STATEFUL_WORKFLOWS_ENABLED` = `False`
- `AGENT_TOOL_EXECUTION_ENABLED` = `False`
- `AGENT_TOOL_REGISTRY_ENABLED` = `False`
- `CLOUD_PROVIDERS_ENABLED` = `False`
- `COMMERCIAL_FEDERATION_ENABLED` = `False`
- `COMMERCIAL_GOVERNANCE_FEDERATION_ENABLED` = `False`
- `DATABASE_URL` = `postgresql+asyncpg://postgres:postgres@localhost:5432/llm_stack`
- `MULTI_CLUSTER_ENABLED` = `False`
- `OBSERVABILITY_ENABLED` = `True`
- `OPERATIONAL_PROFILE` = `standard`
- `PLUGIN_MARKETPLACE_ENABLED` = `False`
- `PROVIDERS_ENABLED` = `local,lmstudio,vllm`
- `RAG_ENABLED` = `True`

### Feature Matrix

- `agents`: `disabled`
- `federation`: `disabled`
- `inference_proxy`: `enabled`
- `loki`: `disabled`
- `marketplace`: `disabled`
- `memory`: `disabled`
- `multi_model`: `enabled`
- `multi_tenant`: `disabled`
- `observability_basic`: `enabled`
- `postgresql`: `enabled`
- `prometheus`: `enabled`
- `rag_basic`: `enabled`
- `sqlite`: `disabled`
- `tempo`: `disabled`
- `tools`: `disabled`
- `workflows`: `disabled`
