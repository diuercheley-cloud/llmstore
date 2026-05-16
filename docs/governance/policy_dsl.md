## Policy DSL

Format:

```json
{
  "version": "1",
  "rules": [
    {
      "name": "block-high-risk",
      "action": "block_if",
      "priority": 200,
      "conditions": [
        {"field": "risk_level", "operator": "eq", "value": "high"}
      ]
    }
  ]
}
```

Supported actions:
- `allow_if`
- `deny_if`
- `require_approval_if`
- `require_dry_run_if`
- `block_if`
- `warn_if`

Supported operators:
- `eq`
- `ne`
- `in`
- `not_in`
- `gt`
- `gte`
- `lt`
- `lte`
- `contains`
- `exists`
