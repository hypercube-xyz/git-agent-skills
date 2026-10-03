# Selected commit replay

Read this when exact commits, ranges, merge commits, empties, or backports need decisions. Resolve selected OIDs before action. In a range `A..B`, `A` is excluded; inspect the expanded commit list and topology, not just the text of the range. Preserve source refs and the target's old OID.

## Dependencies and mainline

Inspect each selected patch, parent, and prerequisite. If a selected change depends on omitted work, either include an explicitly agreed prerequisite or adapt within the approved logical change; do not silently import an entire branch. For a merge commit, inspect both parent diffs and specify `-m <parent-number>` only when the intended mainline is established.

A cherry-pick can become empty because its effect already exists, because conflict resolution canceled it, or because the source commit was intentionally empty. Compare target tree and patch/content equivalence before `--skip` or `--allow-empty`; record the reason.

## Wrong branch and backport

For commits on the wrong branch, first replay and verify them on the intended branch. Cleaning the source is a separate postcondition and belongs to `undo-changes`; never reset the source first. A maintenance backport must also preserve the maintenance line's compatibility, required dependencies, provenance, and focused tests. Publication belongs to `sync-branches`.

After each stop, re-read sequencer state, index stages, and already-created commits. Verify the final target contains each intended logical change once, in order, with no omitted or imported unrelated commits. OID equality is neither required nor forbidden.
