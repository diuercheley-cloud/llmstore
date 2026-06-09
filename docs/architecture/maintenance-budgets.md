# Maintenance Budgets

The platform uses explicit, non-increasing budgets to prevent further surface and
test-debt growth while consolidation proceeds.

`config/maintenance-budgets.json` is enforced by `make maintenance-budgets` and
`make service-coverage-gate`.

Rules:

- Router, service, feature-flag, bootstrap, and settings counts must not increase.
- The collected Python test count must not fall below the baseline.
- Untested P0 and P1 service counts must not increase.
- When a service gains coverage or a surface is removed, reduce the corresponding
  budget in the same change.

The long-term target for both untested P0 and P1 service budgets is zero.
