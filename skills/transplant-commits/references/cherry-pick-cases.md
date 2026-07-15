# Cherry-pick cases

Resolve exact source OIDs and order. Inspect dependencies, merge parents, patch IDs, and target equivalence. Use `-m` only with an established mainline. For empty results, distinguish already-applied, cancellation, and intentionally empty commits before skip/keep. Verify each logical change exactly once and preserve source refs.

## Committed on the wrong branch

Treat moving the intended commits and cleaning the source branch as separate postconditions. First record the source and target OIDs, preserve a recovery ref when needed, and replay the selected commits onto the intended branch. Verify patch equivalence and target tests before any source cleanup. Route an explicitly requested source reversal to `undo-changes`; never reset the source first.

## Maintenance backports

Identify the exact fix and required prerequisite commits before replay. Preserve order, provenance, and compatibility with the maintenance line. Do not broaden a backport into full branch integration, dependency modernization, or unrelated cleanup. Publication of the maintenance ref remains owned by `sync-branches`.
