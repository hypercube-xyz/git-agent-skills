# Shallow and partial-clone repair

## Determine the model

Inspect `.git/shallow`, `extensions.partialClone`, remote promisor/filter config, worktree-specific config, alternates, server capabilities, and the exact missing OIDs. Distinguish:

- intentionally shallow ancestry,
- intentionally promised blobs/trees,
- an object required but not yet materialized,
- a promised object unavailable from the promisor,
- corrupt/inconsistent shallow or promisor metadata.

## Repair choices

- Need more ancestry: deepen by an explicit amount/date or unshallow from the verified source.
- Need specific promised objects: fetch/materialize the exact object/path/history surface and verify its OID/type.
- Need offline operation: enumerate representative build/test/checkout paths and materialize all required objects before disconnecting.
- Promisor unavailable or filter changed: validate destination/source, use a healthier source, or reconstruct a complete clone; do not edit promisor metadata merely to silence errors.
- Broken shallow boundary: preserve the shallow file, compare with source ancestry, and reconstruct/deepen from authoritative refs rather than guessing boundary OIDs.

## Verification

Run exact object reads, required history traversal, representative checkouts, and repository workflows. Bound completeness claims: a repaired partial clone may remain intentionally incomplete outside tested/promised surfaces.
