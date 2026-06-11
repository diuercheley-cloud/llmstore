<!-- synced_from: docs/INSTALL_WIZARD.md -->

> Source of truth: `docs/INSTALL_WIZARD.md`

# Install Wizard

The platform now exposes an interactive operator installer:

```bash
llmstack install
```

For automation:

```bash
llmstack install --non-interactive --target-dir ./deploy/generated
```

## Questions

The wizard collects:

- GPU availability
- NVIDIA / AMD / Apple Silicon
- user count
- multi-tenant requirement
- agentic runtime requirement
- Kubernetes requirement
- full observability requirement
- marketplace requirement

## Generated Files

The wizard writes:

- `docker-compose.yml`
- `.env`
- `profile.yaml`
- `feature-flags.env`

`profile.yaml` records the resolved operational profile and the normalized answers.
`feature-flags.env` contains the explicit feature toggles used by the generated installation.

## Profile Resolution

The wizard maps answers to the official profiles:

- `lite`: small local installs without GPU, agentic runtime, or enterprise requirements.
- `standard`: PostgreSQL plus basic observability and multi-model posture.
- `agentic`: memory, tools, workflows, and agents enabled.
- `enterprise`: multi-tenant, Kubernetes, marketplace, or full observability posture.

## Notes

- Only one accelerator vendor can be selected.
- NVIDIA enables `gpus: all` in the generated Compose file.
- AMD and Apple Silicon are recorded in the generated profile and environment, but Compose stays CPU-compatible.
