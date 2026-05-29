# Few-shot Curation

## Automatic Curation
The platform can automatically curate successful runs into few-shot examples if `AGENT_FEWSHOT_AUTO_CURATOR_ENABLED=true`.

### Curation Criteria
- **Run Status**: Must be `completed`.
- **Eval Score**: Must be above a configurable threshold.
- **Complexity**: Preference for runs that involved multiple tool calls and multi-step reasoning.
- **Safety**: No policy violations or red-team alerts during the run.

### Sanitization
During curation, the `FewShotCurator` performs:
- **Redaction**: Removal of passwords, API keys, and internal system paths.
- **Summarization**: Compressing long tool outputs into concise summaries.
- **Tenant Scoping**: Tagging the example with the correct `tenant_id`.

## Manual Management
Operators can manually activate, deactivate, or delete curated examples via the `/admin/agents/{id}/fewshot-examples` endpoints.
