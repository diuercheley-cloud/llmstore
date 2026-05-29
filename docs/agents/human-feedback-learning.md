# Human Feedback Learning

## Signal Capture
Human feedback is a primary driver for agent improvement. The platform captures multiple types of signals:
- **Thumbs Up/Down**: Binary quality indicator.
- **Correction**: User-provided text that corrects a specific step or the final answer.
- **Approval**: Explicit sign-off from an operator for a high-risk action.
- **Operator Notes**: Internal metadata about why a run was good or bad.

## Learning Loop
When positive feedback is received (`thumbs_up` or `approved`), the system:
1. Identifies the specific `run_id` associated with the feedback.
2. Creates a `LearningCandidate`.
3. Triggers the `LearningPromotionGate` for evaluation.

## Rollback
Each promotion of a learning item creates a versioned rollback point for the agent's definition, allowing operators to revert if a new few-shot example causes regression.
