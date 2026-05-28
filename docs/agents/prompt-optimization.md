# Prompt, Tool, and Policy Optimizers (DSPy-like Optimizer)

The optimization engine features three specialized optimizer components designed to learn from execution history. It acts like a DSPy compiler to refine agent prompts, tool permissions, and policy engine rules.

## Prompt Optimizer

The `PromptOptimizer` dynamically updates system instructions by analyzing historical failure types. 

### How Prompt Compilation Works

1. The optimizer scans the 10 most recent `AgentEvalFailure` entries and failed `AgentRun` executions.
2. Based on the failure classification, it injects structured, high-priority directives into the instruction header:
   
   - **Secret Leak Failures**:
     Appends: `SAFETY: Redact all API keys, tokens, or credentials from responses.`
   
   - **Tool Execution Errors**:
     Appends: `ERROR HANDLING: Verify parameters before calling tools and handle exceptions gracefully.`
   
   - **Policy Engine Denials**:
     Appends: `GOVERNANCE: Respect security boundary limits and policy denials; request approval when needed.`
   
   - **Performance Regression**:
     Appends: `CRITICAL: Ensure performance does not regress on previously passing tasks.`

3. The compiled prompt is structured as:
   ```markdown
   [Original Agent Instructions]

   ### Compiled Directives (DSPy-Optimized):
   - [Applicable Failure Directives]
   ```

---

## Tool Selection Optimizer

The `ToolSelectionOptimizer` prevents agents from executing redundant or error-prone commands by automatically trimming allowed toolsets.

- **Error Analysis**: Calculates failure-to-success ratios for each SaaS connector/tool.
- **Pruning**: If a tool repeatedly triggers exceptions or access boundaries failures (exceeding failure thresholds), the optimizer suggests removing it from the agent's allowed tools list.
- **Optimization Strategy**: Focuses the agent's tools list on high-confidence tools, minimizing hallucinated tool calls and API limits errors.

---

## Policy Optimizer

The `PolicyOptimizer` resolves security blocks and policy engine denials by generating custom rules to address governance issues.

- **Rule Generation**: Generates explicit rules tailored to allow specific actions while enforcing strict boundary limitations.
- **Rule Verification**: Policy updates are registered under `AgentPolicyCandidate` and validated against the rego/OPA enforcement engine during candidates evaluation.
- **Safety Blocks**: If a policy rule introduces a regression (such as bypassing data boundary restrictions), the promotion gate blocks the candidate.
