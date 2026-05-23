# Reasoning Loops

The Agentic AI Platform supports advanced reasoning strategies to improve task execution accuracy and reliability. These loops extend the standard direct LLM call with structured cycles like ReAct and Plan-and-Solve.

## ReAct (Thought/Action/Observation)

The ReAct loop enables agents to reason about their next step before taking action.
- **Thought**: The LLM analyzes the current state and goal.
- **Action**: The LLM selects a tool and provides parameters.
- **Observation**: The agent executes the tool and provides the result back to the LLM.

### Governance
- `AGENT_REACT_LOOP_ENABLED`: Enables the ReAct cycle.
- Raw Chain-of-Thought (CoT) is sanitized and only summaries are logged to prevent sensitive data leakage.

## Plan-and-Solve

For complex multi-step tasks, the Plan-and-Solve strategy first generates a comprehensive plan before executing steps.
- **Plan**: A list of discrete tasks with dependencies.
- **Validation**: The plan is validated against schemas and policies.
- **Execution**: Steps are executed sequentially or in parallel.

## Structured Output and Repair

To ensure reliability, the platform validates all LLM outputs against expected JSON schemas.
- `AGENT_STRUCTURED_OUTPUT_RETRY_ENABLED`: Enables automatic repair attempts if the LLM provides malformed JSON.
- **Repair Prompt**: If validation fails, a targeted prompt is sent back to the LLM with the error details.
- `max_repair_attempts`: Limits the number of retries per step.
