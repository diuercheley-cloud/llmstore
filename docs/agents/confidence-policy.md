# Confidence Policy

## Policy Definition
Uncertainty policies are scoped per agent and define the minimum acceptable confidence for autonomous operation.

### Class-Based Thresholds
By default, the system applies thresholds based on the `agent_class`:
- **Compliance/Security**: 0.9 (Strict - almost zero tolerance for uncertainty).
- **Support**: 0.7 (Balanced - requires solid evidence but allows some ambiguity).
- **Creative**: 0.4 (Relaxed - prioritizes output generation over evidentiary proof).

### Configuration
Policies can be updated via `POST /admin/agents/{id}/uncertainty-policy`:
```json
{
  "min_confidence_threshold": 0.85,
  "auto_research_enabled": true,
  "hitl_on_low_confidence": true
}
```

## Evidence Gaps
When a policy is triggered, the `EvidenceGapDetector` identifies the root cause (e.g., lack of source coverage) and suggests specific tools to resolve the gap. This information is stored in `agent_evidence_gaps` and included in uncertainty events.
