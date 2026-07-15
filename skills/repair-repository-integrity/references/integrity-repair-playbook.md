# Integrity repair playbook

## Classify

- Ref failure: loose/packed ref syntax, target OID, reflog, namespace collision.
- Object failure: exact OID/type, loose versus packed, checksum/read failure.
- Pack failure: `.pack`/`.idx` pairing, index verification, interrupted maintenance.
- Shared-store failure: alternates path, permissions, lifecycle, and source health.
- Storage failure: I/O errors, disk/full/bit-rot signals; stop writes first.

## Recovery-source order

Prefer a verified healthy remote/clone, immutable bundle/backup, or target-scoped artifact. Validate source refs/objects before transfer. Never use the damaged repository as the sole authority for what is healthy.

## Action preference

1. Preserve exact damaged state and local-only refs/worktrees.
2. Reconstruct in quarantine or a fresh clone.
3. Acquire exact missing objects or rebuild indexes without deleting original packs.
4. Repair exact refs only after object targets validate.
5. Replay local-only state and compare refs/content.
6. Cut over after acceptance; keep rollback/evidence until stable.

Do not use `prune`, expire reflogs, delete packs, or run aggressive repack as an exploratory step.
