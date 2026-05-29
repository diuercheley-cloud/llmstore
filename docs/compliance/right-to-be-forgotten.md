# Right to be Forgotten

## Compliance Posture
The Right to be Forgotten (RTBF) enables end-users to explicitly mandate the removal of their personal data from cognitive models and vector embeddings.

### Core Flows
1. **Consent Revocation**: When `revoke_consent` is invoked, `AgentMemoryConsent` state shifts to `revoked`. Active retrievers check consent status implicitly. If consent is absent or revoked, the memory block is entirely ignored during downstream prompting.
2. **Explicit Deletion**: When an explicit deletion is requested, the system uses the `MemoryErasureService` to either wipe the row natively or tombstone it, clearing `raw_content` and updating its `status`.
3. **Auditability**: `get_deletion_proof(tenant_id, item_id)` returns cryptographic assurance that the `raw_content` of an item no longer exists within the system boundaries.

These primitives ensure that AI agents respect jurisdictional compliance constraints concerning user data lifecycle.
