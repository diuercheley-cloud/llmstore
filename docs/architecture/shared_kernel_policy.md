## Shared Kernel Policy

The shared kernel must stay minimal.

Allowed shared kernel categories:
- time helpers
- hashing helpers
- database session primitives
- generic request context and logging primitives

Disallowed shared kernel growth:
- domain-specific models
- domain-specific enums without platform-wide justification
- orchestration logic
- direct runtime or external integration behavior

Every new shared kernel dependency must remain:
- deterministic
- offline-first
- tenant-safe
- free from real external execution side effects
