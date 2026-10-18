# Integrity repair playbook

Read this when ordinary Git refs, objects, packs, or alternates are damaged. Stop garbage collection, pruning, aggressive maintenance, reset, and destructive checkout until local-only state and diagnostics are preserved.

## Classify exact failure

- Ref: inspect loose/packed syntax, direct versus symbolic kind (including dangling symbolic refs), target OID, namespace collisions, reflog, and whether the target object exists. An ordinary `update-ref` follows a symbolic ref; use `--no-deref` plus expected old OID only for a verified direct ref. Changing a symbolic target requires a feature-checked old-target compare-and-swap transaction or a stop.
- Before changing a ref, list every worktree with that branch checked out. Preserve its index and actual file bytes, including hidden edits, and reconcile its HEAD/index/worktree through an explicit accepted transition. For diagnosis or trial repair, correct an inactive ref in quarantine; do not move a checked-out branch merely because the replacement OID validates.
- Object: record exact OID/type, loose versus packed location, checksum/read failure, and which refs or trees require it.
- Pack: identify `.pack`/`.idx` pairing and whether an interrupted write or storage error occurred; do not delete the original pack while testing an index rebuild.
- Alternate/shared store: inspect path, permissions, lifecycle, and source health. An object readable only through an alternate is not independently materialized.
- Storage: I/O, disk-full, or bit-rot signals require stopping writes and assessing the filesystem before repository repair.

Use bounded object/ref reads first; interpret `git fsck` in the context of shallow and promisor semantics. Do not label an intentionally promised blob as corruption merely because it is absent locally.

## Recovery source and action

Prefer a verified healthy remote/clone, immutable bundle/backup, or exact target-scoped artifact. Validate source object type and bytes against its OID, as well as provenance and completeness for the required ref. Never treat the damaged target as the sole authority.

1. Preserve the damaged repository, reflogs, local-only refs, worktrees, index, untracked/ignored files, and exact errors.
2. Reconstruct in quarantine or a fresh clone when feasible. Use additive object acquisition, exact ref correction with any attached-worktree transition accounted for, or index rebuild without deleting original evidence.
3. Materialize objects before retiring an alternate. Replay local-only state only after its OIDs and content are validated.
4. Test required refs, object reads, history traversal, checkout, and representative repository workflow in quarantine; then accept a cutover with a recovery copy retained.

If damage expands or storage remains unreliable, stop. A successful fetch or fsck command does not establish that every required object and protected local state survived.
