# Partial clone and sparse checkout for performance

This reference owns intentional performance policy in a healthy repository.

- Inspect filter, promisor remote, sparse patterns/cone mode, worktree-specific config, required offline workflows, and tooling compatibility.
- Change one dimension at a time and measure fetch/checkout/status behavior.
- Materialize objects required for known offline/build paths before disconnecting.
- Do not claim storage savings until object/pack measurements confirm them.
- If required objects cannot be materialized or promisor/shallow metadata is inconsistent, stop optimization and route to `repair-repository-integrity`.
