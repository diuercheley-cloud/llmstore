# Cognitive Loopback

## Overview
Cognitive Loopback is a self-improvement mechanism that allows AI agents to learn from their own successful executions, human feedback, and formal evaluations. It creates a closed-loop system where performance data is recycled into "Few-shot" examples or refined reasoning patterns.

## Architecture
The subsystem is composed of several specialized services:
- **Feedback Collector**: Captures human signals (thumbs up/down, corrections).
- **Success Pattern Miner**: Analyzes completed agent runs for high-quality reasoning and tool sequences.
- **Learning Candidate Registry**: Stores potential learning items before they are promoted to production.
- **Learning Promotion Gate**: Enforces safety, privacy, and quality checks (Evals) before activating a learning.

## Learning Lifecycle
1. **Extraction**: A run completes or feedback is received.
2. **Candidate Generation**: Data is sanitized (secrets removed, PII filtered).
3. **Evaluation**: Automated evals score the candidate.
4. **Human Review**: Operators approve or reject the learning.
5. **Promotion**: The candidate becomes an active Few-Shot example for the agent.

## Governance
Learning is never automatically applied to production by default. 
- `AGENT_AUTO_APPLY_LEARNINGS=true` enables autonomous learning, bypassing human-in-the-loop review.
- Tenant isolation is strictly enforced; learnings from Tenant A never leak to Tenant B.
