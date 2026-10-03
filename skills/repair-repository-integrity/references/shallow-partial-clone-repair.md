# Shallow and partial-clone repair

Read this for shallow boundaries, promisor remotes, object filters, lazy materialization, or offline completeness. Inspect the actual common Git directory; a linked worktree's `.git` may be a file.

## Determine the model

Inspect `git rev-parse --is-shallow-repository`, the shallow file via `git rev-parse --git-path shallow`, partial-clone extensions/promisor and filter config, alternates, server capability, and exact required OIDs. Distinguish:

- intentionally shallow ancestry,
- intentionally promised blobs/trees,
- a required object merely not materialized yet,
- a promised object unavailable from the promisor,
- corrupt or inconsistent shallow/promisor metadata.

Prevent implicit lazy fetch during local-only diagnosis. A normal object read can contact the promisor; report an unavailable offline check rather than silently using network.

## Choose bounded repair

- Need more ancestry: deepen by a reviewed count/date or unshallow from the verified source, then verify the exact merge-base/history question.
- Need selected promised objects: materialize the required object/path/workflow surface from the intended promisor, then verify OID/type and local readability with lazy fetch disabled.
- Need offline operation: enumerate representative build/test/checkout paths and materialize their dependencies before disconnecting.
- Promisor unavailable or filter changed: validate source/destination and reconstruct a healthier clone where necessary; do not hand-edit metadata to silence errors.
- Broken shallow boundary: preserve the file and compare ancestry with source; reconstruct/deepen from authoritative refs instead of guessing boundary OIDs.

Verify required object reads, history traversal, representative checkouts, and workflow behavior. A repaired partial clone may remain intentionally incomplete outside tested surfaces; state that limit explicitly.
