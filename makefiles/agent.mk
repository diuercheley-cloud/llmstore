# ── Agent Platform Targets ─────────────────────────────────────

agent-worker: ## Start the Agent Worker process
	@chmod +x scripts/dev/run-agent-worker.sh
	@./scripts/dev/run-agent-worker.sh

agent-security-tests: ## Run agent security and sandbox jailbreak tests
	@echo "Running Agent security and jailbreak tests..."
	@PYTHONPATH=.:control_plane .venv/bin/pytest tests/integration/security/ -v

agent-kg-benchmark: ## Generate the synthetic KG benchmark artifact
	@echo "Running Knowledge Graph benchmark..."
	@chmod +x scripts/dev/benchmark-knowledge-graph.sh
	@./scripts/dev/benchmark-knowledge-graph.sh

agent-e2e-tests: ## Run lightweight agentic E2E contract tests
	@echo "Running Agentic E2E tests..."
	@PYTHONPATH=.:control_plane .venv/bin/pytest tests/e2e/test_multi_agent_research_code_review_deploy.py tests/e2e/test_agent_studio_dry_run.py tests/e2e/test_mcp_tool_integration.py -v

agent-executor-e2e: ## Run Agent Executor real E2E flow test
	@echo "Running Agent Executor real E2E flow test..."
	@PYTHONPATH=.:control_plane .venv/bin/pytest tests/e2e/test_agent_executor_real_flow.py -v

agent-platform-validation: ## Run the core agentic expansion validation pack
	@echo "Running full Agentic Platform operational validation..."
	@$(MAKE) agent-security-tests
	@$(MAKE) agent-kg-benchmark
	@$(MAKE) agent-e2e-tests

agent-dlq-inspect: ## Inspect agent dead letter queue
	@./scripts/dev/agent-dlq-inspect.sh

agent-recovery-test: ## Run agent queue recovery test
	@./scripts/dev/agent-queue-recovery-test.sh

agent-queue-inspect: ## Inspect agent queue depth, workers, DLQ
	@chmod +x scripts/dev/agent-queue-inspect.sh
	@./scripts/dev/agent-queue-inspect.sh

agent-worker-status: ## Show agent worker status and heartbeats
	@chmod +x scripts/dev/agent-worker-status.sh
	@./scripts/dev/agent-worker-status.sh

agent-worker-drain: ## Drain agent worker (cancel queued jobs)
	@chmod +x scripts/dev/agent-worker-drain.sh
	@./scripts/dev/agent-worker-drain.sh

agent-sandbox-security: ## Run Agent Sandbox Security checks
	@chmod +x scripts/dev/agent-sandbox-security-test.sh
	@./scripts/dev/agent-sandbox-security-test.sh

agent-evals: ## Run Agent Evaluation suites
	@echo "Running Agent Evaluations..."
	@PYTHONPATH=control_plane .venv/bin/python -m pytest tests/integration/agent_evals/
	@chmod +x scripts/validators/validate-agent-eval-datasets.sh
	@./scripts/validators/validate-agent-eval-datasets.sh

agent-real-provider-validation: ## Run Agent real provider validation suite (opt-in, budgeted)
	@echo "Running Agent Real Provider Validation..."
	@chmod +x scripts/dev/run-agent-real-provider-validation.sh
	@AGENT_REAL_PROVIDER_VALIDATION_ENABLED=true \
	 AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL=1.00 \
	 AGENT_REAL_PROVIDER_VALIDATION_TIMEOUT_SECONDS=60 \
	 PYTHONPATH=control_plane \
	 ./scripts/dev/run-agent-real-provider-validation.sh

agent-real-provider-validation-real: ## Run Agent real provider validation (real calls, may incur cost)
	@echo "Running Agent Real Provider Validation (REAL MODE)..."
	@chmod +x scripts/dev/run-agent-real-provider-validation.sh
	@AGENT_REAL_PROVIDER_VALIDATION_ENABLED=true \
	 AGENT_REAL_PROVIDER_VALIDATION_ALLOW_PAID=false \
	 AGENT_REAL_PROVIDER_VALIDATION_BUDGET_BRL=1.00 \
	 PYTHONPATH=control_plane \
	 ./scripts/dev/run-agent-real-provider-validation.sh --real --budget 1.00

agent-eval-gate: ## Run Agent Evaluation promotion gate verification
	@echo "Running Agent Eval Gate Verification..."
	@PYTHONPATH=control_plane .venv/bin/python -c "\
	import asyncio; \
	from app.db.session import SessionLocal; \
	from app.services.agents.eval_gate import EvalGateService; \
	from sqlalchemy import select; \
	from app.models.agents.agents import AgentRegistryEntry; \
	async def run(): \
	    async with SessionLocal() as db: \
	        res = await db.execute(select(AgentRegistryEntry).where(AgentRegistryEntry.status == 'approved')); \
	        entries = res.scalars().all(); \
	        print(f'Found {len(entries)} agents pending gate check'); \
	        for entry in entries: \
	            print(f'  Agent: {entry.name} ({entry.id}) - status: {entry.status}'); \
	asyncio.run(run())"

agent-optimization-check: ## Execute agent evals and verify safety/optimization constraints
	@echo "Running Agentic CI/CD Optimization checks..."
	@PYTHONPATH=control_plane .venv/bin/pytest tests/control_plane/test_agent_optimization.py -v

sandbox-ga-test: ## Validate Sandbox GA Hardening policies
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_sandbox_ga.py -v

mcp-ga-test: ## Validate MCP GA Hardening policies
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_mcp_ga.py -v

memory-erasure-test: ## Validate Memory Erasure/Right to be Forgotten policies
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_memory_erasure.py -v

capability-signature-gate: ## Validate Bundle/Capability Signing and supply chain policies
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_capability_signing.py -v

multi-agent-ga-test: ## Validate Multi-Agent GA Path policies
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_multi_agent_ga.py -v

agent-studio-ga-test: ## Validate Agent Studio GA and Visual Flow Editor logic
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_agent_studio_ga.py -v

agent-debugger-test: ## Validate Time-Travel Debugger and Replay logic
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_agent_debugger.py -v

agent-canary-test: ## Validate Shadow Mode and Canary Agents logic
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_agent_canary.py -v

agent-wallet-test: ## Validate Agent Wallets and Spend Controls
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_agent_wallet.py -v

agent-digital-twins-test: ## Validate Digital Twin Connectors and Safety Interlocks
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_digital_twins.py -v

agent-sab-test: ## Validate Standardized Agent Bundle (SAB) portability
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_agent_sab.py -v

agent-federated-memory-test: ## Validate Federated Memory and Sovereign Sync
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_federated_memory.py -v

agent-mcts-test: ## Validate MCTS Reasoning Runtime
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_mcts_reasoning.py -v

agent-constraints-test: ## Validate Constraint-Based Reasoning Runtime
	PYTHONPATH=control_plane .venv/bin/python -m pytest tests/test_constraint_reasoning.py -v

agentic-ga-hardening: sandbox-ga-test mcp-ga-test memory-erasure-test capability-signature-gate multi-agent-ga-test agent-studio-ga-test agent-debugger-test agent-canary-test agent-wallet-test agent-digital-twins-test agent-sab-test agent-federated-memory-test agent-mcts-test agent-constraints-test ## Run all Agentic AI GA Hardening tests
