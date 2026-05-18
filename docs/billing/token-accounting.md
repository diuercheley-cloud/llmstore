# Token Accounting

Token accounting is the process of tracking and recording token usage for billing and quota purposes.

## Accuracy

By default, the system attempts to use real tokenizers for maximum accuracy. When a real tokenizer is used:
- Invoices reflect exact token usage.
- Quotas are strictly enforced based on real counts.

## Fallback Estimation

When a real tokenizer is not available (e.g., unknown model or missing library), the system falls back to an estimation method.
- Records are marked with `tokens_estimated = true`.
- The method field is set to `estimated`.

## Billing Reconciliation

Administrative dashboards show the tokenization method used for each request group. This allows for transparency and reconciliation when usage seems higher or lower than expected due to estimation heuristics.
