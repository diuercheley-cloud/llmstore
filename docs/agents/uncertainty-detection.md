# Epistemic Uncertainty Detection

## Overview
Epistemic Uncertainty Detection allows agents to quantify their own confidence level before delivering a final response. This mechanism prevents "confident hallucinations" by identifying when the agent lacks sufficient evidence or faces contradictory information.

## Metrics
Confidence is calculated based on several weighted metrics:
- **Evidence Score**: Quantifies the amount and quality of retrieved information.
- **Contradiction Score**: Measures the degree of conflict between different tool results or memory blocks.
- **Source Coverage**: Evaluates if all parts of the user query are addressed by the available data.
- **Consistency**: Checks if repetitive tool calls (if any) produce stable outputs.

## Calibration
The `ConfidenceCalibrator` uses a weighted formula to produce a score between 0.0 and 1.0. High contradiction scores act as a significant penalty, overriding high evidence volume.

## Actions on Low Confidence
When confidence falls below the threshold defined in the `UncertaintyPolicy`, the agent can:
1. **Auto-Research**: Trigger additional tool calls (e.g., `web_search`) to fill evidence gaps.
2. **Human-in-the-Loop (HITL)**: Escalate the run to a human operator for review or manual tool execution.
3. **Explicit Uncertainty**: Return a response that acknowledges the lack of information or the presence of a conflict.

## Usage
Enable uncertainty detection via `AGENT_UNCERTAINTY_DETECTION_ENABLED=true`.
Monitor events via `GET /admin/agents/{id}/uncertainty-events`.
