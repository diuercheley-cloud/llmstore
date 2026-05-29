---
owner: platform-ops
status: consolidated
---

# Provider Validation Matrix

## Purpose

The Provider Validation Matrix maps each supported provider's feature coverage
for the 8 mandatory agentic validations. It is auto-generated after each
validation suite run and stored in
`artifacts/evals/real-provider-validation/latest/provider-matrix.md`.

## Matrix Schema

| Provider | Basic Call | Structured Output | Tool Call | Memory Injection | Context Compression | Fallback | Budget Guard | Timeout Guard | Overall |
|----------|:----------:|:-----------------:|:---------:|:----------------:|:-------------------:|:--------:|:------------:|:-------------:|:-------:|
| mock | ✓ | ✓ | ✓ | ✓ | ✓ | – | ✓ | – | PASSED |
| local_gateway | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PASSED |
| openrouter | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PASSED |
| openai_compatible_custom | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | PASSED |
| local_llama_cpp | ✓ | ✓ | ~ | ✓ | ✓ | ✓ | ✓ | ✓ | DEGRADED |

## Legend

- ✓ = Passed
- ~ = Degraded (feature partially supported or limited)
- ✗ = Failed
- – = Skipped (not applicable)
- ! = Error

## Provider Limitations

| Provider | Limitation |
|----------|------------|
| `mock` | Fallback and timeout guard not applicable (instant responses) |
| `local_gateway` | Requires running inference proxy |
| `local_llama_cpp` | Tool calling may not be supported; marked degraded |
| `openrouter` | Requires API key; may incur cost |
| `openai_compatible_custom` | Requires API key and endpoint; may incur cost |

## Validation Descriptions

| Validation | What It Tests |
|------------|---------------|
| **basic_model_call** | Provider responds with non-empty content and returns usage metrics |
| **structured_output** | Provider respects JSON schema response_format, retries on malformed output |
| **tool_call_format** | Provider emits correct tool_call wire format (id, type, function) |
| **memory_injection** | Provider uses synthetic memory context injected via system prompt |
| **context_compression** | Provider preserves goal after 20-turn history |
| **fallback** | System degrades gracefully to alternative provider on primary failure |
| **budget_guard** | Suite stops executing when cumulative cost exceeds budget |
| **timeout_guard** | Provider request times out with explicit error on unreachable endpoint |
