---
owner: platform-ops
status: consolidated
---

# Semantic Layer

The Semantic Layer provides abstraction over raw text, structuring knowledge so agents can systematically reason about dependencies and hierarchies.

## Schema
- **Entity Types:** `person`, `organization`, `project`, `system`, `contract`, `document`, `process`, `asset`, `risk`, `ticket`, `repository`, `agent`, `tool`
- **Relation Types:** `owns`, `depends_on`, `manages`, `references`, `blocks`, `implements`, `violates`, `approves`, `uses`, `belongs_to`, `related_to`

This uniform schema guarantees predictable reasoning for complex tasks like root cause analysis or architectural duplication detection.
