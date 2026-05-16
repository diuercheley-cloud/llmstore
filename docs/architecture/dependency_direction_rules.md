## Dependency Direction Rules

Allowed:
- same-domain imports
- imports from `app.core`
- imports from `app.db`
- imports from `app.domains.<peer>.contracts`
- imports from `app.domains.<peer>.events`

Forbidden:
- importing `schemas.py` from another domain
- importing another domain package root as a shortcut
- wildcard imports from peer domains
- direct access to peer domain models
- circular dependencies between bounded contexts

Intent:
- public surfaces stay explicit
- internal details do not become accidental platform APIs
- future extraction into separate modules remains feasible
