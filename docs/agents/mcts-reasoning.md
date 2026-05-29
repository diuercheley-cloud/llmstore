# MCTS Reasoning Runtime

## Overview
The Monte Carlo Tree Search (MCTS) Reasoning Runtime provides agents with the ability to "look ahead" and simulate multiple future execution paths before committing to a real-world action. This is particularly useful for complex decision-making tasks where the cost of failure is high or where multiple tool sequences must be evaluated.

## Core Loop
The MCTS runtime follows the standard search cycle:
1. **Selection**: Traverses the existing tree using the Upper Confidence Bound for Trees (UCT) formula to balance exploration and exploitation.
2. **Expansion**: Adds a new child node to the tree by taking an untried action.
3. **Simulation (Rollout)**: Plays out the rest of the task from the new node until a terminal state is reached, using the `RolloutPolicy`.
4. **Backpropagation**: Propagates the outcome score (reward) from the simulation back up the tree, updating node statistics.

## Components
- **State Node**: Stores the state snapshot and visit/value statistics.
- **Rollout Policy**: Determines the heuristic or stochastic strategy for simulations.
- **Value Estimator**: Assigns a success score (0.0 to 1.0) to terminal states.
- **Simulation Sandbox**: A safe environment (gVisor/Firecracker) where tools can be simulated without real-world side effects.

## Safety and Governance
- **Budget Limits**: Max rollouts, depth, time, and computational cost are strictly enforced.
- **Side-Effect Isolation**: Simulations are strictly prohibited from performing destructive or external actions unless explicitly authorized by a specialized policy.
- **Privacy**: Raw Chain-of-Thought data from simulations is summarized and redacted before being logged to the decision tree.

## Configuration
- `AGENT_MCTS_REASONING_ENABLED`: Enables the MCTS runtime.
- `AGENT_MCTS_SANDBOX_SIMULATION_ENABLED`: Allows the use of hardened sandboxes for high-fidelity simulations.
