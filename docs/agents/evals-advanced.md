# Advanced Agent Evaluations

The Advanced Evaluation System goes beyond simple assertions to measure agent quality, safety, and comparative performance.

## Key Features

- **LLM-as-a-Judge**: Automated, rubric-based scoring using high-capability models.
- **Red-Teaming**: Adversarial testing for jailbreaks, prompt injections, and data exfiltration.
- **A/B Comparisons**: Side-by-side pairwise scoring of different agent versions.
- **Promotion Gates**: Automated thresholds and safety checks before production deployment.

## Evaluation Workflow

1. **Define Dataset**: Register inputs and expected behaviors.
2. **Execute Run**: Run the agent against the dataset using a specific provider (Mock, Gateway, or Real).
3. **Judge Results**: Use an LLM judge to score the outputs based on a versioned rubric.
4. **Adversarial Scanning**: Run red-team suites to check for security vulnerabilities.
5. **Verify Readiness**: The EvalScoringManager validates if the run meets the promotion criteria.

## Promotion Criteria

Promotion to production is blocked if:
- Aggregate score is below the configured threshold (default 0.8).
- Mock LLM judge results are detected (ensuring real verification).
- Safety violations are found during red-team scanning.
- A regression is detected compared to the current production baseline.
