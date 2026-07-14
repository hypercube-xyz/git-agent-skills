# Secret-handling controls

Use tools that can suppress/redact values. Capture only type, path, line/commit, confidence, and an
opaque identifier.

## Safe deduplication

1. Prefer a scanner-generated finding ID that is not derived directly from the secret.
2. If a run-local fingerprint is required, compute HMAC-SHA-256 with a random ephemeral key held
   only in memory and discard the key after the run.
3. Do not claim an unkeyed truncated hash is non-reversible for passwords or other low-entropy
   material.

## Exposure response

- Stop further publication.
- Rotate/revoke the credential through an authorized provider workflow.
- Determine whether it appears in worktree, index, local commits, or published refs.
- Remove from current content and add appropriate preventive controls.
- Consider history rewrite only after rotation, scope/consumer analysis, backup, approval, and an
  exact publication plan.

A scan with missing objects, excluded paths, unavailable submodules, or unsupported binary formats
must be reported as partial.
