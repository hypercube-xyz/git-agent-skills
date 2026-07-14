# Cherry-pick cases

Review immutable OIDs and diffs before replay. Range notation can be surprising:

- `A..B` excludes `A` and includes commits reachable from `B` but not `A`.
- `A^..B` can include `A`.
- `--no-walk` affects ordering for explicitly listed commits.

For a merge commit, `git cherry-pick -m <parent-number> <merge-oid>` defines the parent used as the
mainline. Inspect all parents and the change relative to each; never guess `-m 1`.

An empty result can mean the patch is already present. Compare trees/diffs or use patch-equivalence
signals; do not automatically skip or create an empty commit.

Cherry-pick reuses author information and commit message but creates a commit from the resulting
tree, parent, and metadata. If every serialized field happens to match an existing commit, the OID
can match too; therefore verify semantics and topology rather than asserting a fresh ID.
