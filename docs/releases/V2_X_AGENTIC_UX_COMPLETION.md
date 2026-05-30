# v2.x-agentic-ux-completion

Date: 2026-05-30

## Goal

Complete the agentic UX surface by delivering persistent sessions, prompt template engine, end-user chat, consistent frontend routing, PWA/mobile foundation, voice/WebRTC foundation, agent-as-API deployment, and bundle developer workflow.

## Scope

1. **Sessões/threads persistentes** — agent session CRUD, session-aware executor, session state persistence.
2. **Prompt template engine** — versioned templates, registry, renderer, validator, playground.
3. **Chat final de usuário** — real chat with persistent sessions, streaming, mobile-responsive.
4. **Rotas para frontends órfãos** — navigation system, layout, command palette, route definitions.
5. **PWA/mobile foundation** — service worker, manifest, offline page, mobile components.
6. **Voz/WebRTC foundation** — voice agent, STT/TTS streaming, WebRTC audio/voice flags.
7. **Agent-as-API deployment** — deployment API, facade, runtime management.
8. **Navegação consistente** — admin hub layout, sidebar, command palette, code splitting.
9. **Bundle developer workflow** — init, sign, validate, test, publish scripts + web UI.

## Release Criteria

- End-user has real chat with persistent sessions.
- Orphan frontends are accessible via consistent navigation.
- Prompts are versioned with full lifecycle management.
- Agent can be deployed as a standalone API.
- Working tree is clean.
- All release gates pass.

## Validation

- `make test`
- `make validate-quick`
- `make security`
- `make operational-readiness`
- `make agentic-readiness`
- `make production-agentic-e2e`
- `make platform-freeze-check`
- `make feature-flag-audit`
- `make release-gate TAG=v2.x-agentic-ux-completion`
- `bash scripts/check-secrets.sh --all`
- `scripts/check-alembic-integrity.sh`
