<!-- AUTO-GENERATED: do not edit manually -->


# Platform Profiles

Available operational profiles and their characteristic feature sets.

## Profile: `agentic`

Standard profile extended with memory, tools, workflows, and agents.

### Feature Set

| Feature | Enabled |
| --- | --- |
| `agents` | ✅ |
| `federation` | ❌ |
| `inference_proxy` | ✅ |
| `loki` | ❌ |
| `marketplace` | ❌ |
| `memory` | ✅ |
| `multi_model` | ✅ |
| `multi_tenant` | ❌ |
| `observability_basic` | ✅ |
| `postgresql` | ✅ |
| `prometheus` | ✅ |
| `rag_basic` | ✅ |
| `sqlite` | ❌ |
| `tempo` | ❌ |
| `tools` | ✅ |
| `workflows` | ✅ |

## Profile: `enterprise`

Full platform profile with enterprise observability, tenancy, federation, and marketplace.

### Feature Set

| Feature | Enabled |
| --- | --- |
| `agents` | ✅ |
| `federation` | ✅ |
| `inference_proxy` | ✅ |
| `loki` | ✅ |
| `marketplace` | ✅ |
| `memory` | ✅ |
| `multi_model` | ✅ |
| `multi_tenant` | ✅ |
| `observability_basic` | ✅ |
| `postgresql` | ✅ |
| `prometheus` | ✅ |
| `rag_basic` | ✅ |
| `sqlite` | ❌ |
| `tempo` | ✅ |
| `tools` | ✅ |
| `workflows` | ✅ |

## Profile: `lite`

Local profile with the minimum services required for inference and basic RAG.

### Feature Set

| Feature | Enabled |
| --- | --- |
| `agents` | ❌ |
| `federation` | ❌ |
| `inference_proxy` | ✅ |
| `loki` | ❌ |
| `marketplace` | ❌ |
| `memory` | ❌ |
| `multi_model` | ❌ |
| `multi_tenant` | ❌ |
| `observability_basic` | ❌ |
| `postgresql` | ❌ |
| `prometheus` | ❌ |
| `rag_basic` | ✅ |
| `sqlite` | ✅ |
| `tempo` | ❌ |
| `tools` | ❌ |
| `workflows` | ❌ |

## Profile: `local`

No description

## Profile: `standard`

PostgreSQL profile with basic observability and multi-model inference.

### Feature Set

| Feature | Enabled |
| --- | --- |
| `agents` | ❌ |
| `federation` | ❌ |
| `inference_proxy` | ✅ |
| `loki` | ❌ |
| `marketplace` | ❌ |
| `memory` | ❌ |
| `multi_model` | ✅ |
| `multi_tenant` | ❌ |
| `observability_basic` | ✅ |
| `postgresql` | ✅ |
| `prometheus` | ✅ |
| `rag_basic` | ✅ |
| `sqlite` | ❌ |
| `tempo` | ❌ |
| `tools` | ❌ |
| `workflows` | ❌ |
