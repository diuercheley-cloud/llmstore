# Hallucination Guard

## Goal
The Hallucination Guard is a specialized component of the Meta-Reviewer focused on detecting and mitigating factual inconsistencies (hallucinations) in agent responses.

## Methodology
The guard uses a multi-step verification process:
1. **Evidence Extraction**: Resolving all tool outputs and memory context used by the agent during the current run.
2. **Claim Analysis**: Identifying factual claims in the candidate response.
3. **Cross-Reference**: Comparing each claim against the extracted evidence.
4. **Scoring**: Generating a factual consistency score.

## Findings
- **Unsupported Claims**: Findings generated when the agent makes a factual statement for which no evidence was found in the context.
- **Contradictory Claims**: Findings generated when the agent's statement directly conflicts with retrieved evidence.
- **Confabulation**: Detects when the agent invents tool outputs or internal states that did not occur.

## Corrective Actions
- **Require Revision**: Prompts the agent to re-evaluate its reasoning based on the reviewer's findings.
- **Block**: Prevents the delivery of responses that contain critical factual errors.
