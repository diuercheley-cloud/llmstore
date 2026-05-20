# Release Summary: v1.9.8-platform-consolidation

## Intent

`v1.9.8-platform-consolidation` is a freeze-and-optimize release. It consolidates supportability, runtime-profile governance, API surface classification, and complexity reporting inside existing administrative and operational areas. It does **not** introduce a new major bounded context.

## Outcome

- Platform freeze rules pass after classifying the `/admin/support` surface and support-bundle service.
- Documentation was aligned to the consolidation objective and to the advisory/experimental positioning rules.
- The client portal static asset regression was fixed by mounting `/static` in the FastAPI app, restoring `/static/portal/portal.js`.
- Release support artifacts were generated for validation, complexity, supported surface, and performance.

## Release Positioning

- SOC 2 / ISO content remains readiness-oriented only.
- Advisory controls remain advisory.
- Experimental capabilities remain experimental.
- Support bundles remain operator-only and sanitized; no prompts, documents, `.env` files, or real secrets belong in release artifacts.
