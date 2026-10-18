# Restacking a branch DAG

Read this when a parent/base moved or equivalent changes may already have landed. Record for every node: old parent OID, old tip OID, intended logical diff, new parent OID, current worktree, and a recovery ref outside `refs/heads/`. Freeze these before changing a child.

## Determine what already landed

- Merge: ancestry may prove the old parent is included, but still compare the child's isolated diff against the intended new parent.
- Rebase: commit IDs differ; use `range-diff` and inspect resulting content. Patch equivalence alone can miss context-dependent behavior.
- Squash: old ancestry disappears. Compare patch IDs/content and behavior on the new parent; do not drop a child commit from subject similarity.
- Empty layer: accept only when its full intended change is verified on the new parent and the review boundary may disappear under the agreed plan.

For a linear child whose old parent is the exact boundary, `git rebase --onto <new-parent-oid> <old-parent-oid> <child>` expresses the move. Merge commits, prior cherry-picks, or a non-ancestor old parent need a different reviewed plan. Disable implicit `rebase.updateRefs` unless its entire affected set is in scope. Separately inspect effective `notes.rewrite.rebase`, `notes.rewriteRef`, and `GIT_NOTES_REWRITE_REF`; a rebase can rewrite notes refs even with `rebase.updateRefs` disabled. Disable notes rewriting for a branch-only restack with invocation-scoped `-c notes.rewrite.rebase=false`, accounting for effective configuration/environment, or record each affected notes ref's old OID, preserve it, and review its new state. Disable implicit autostash with `-c rebase.autoStash=false` unless its effects on local work are reviewed.

Restack bottom-up. At each layer, check sequencer completion, new base/tip OIDs, isolated review diff, omitted/duplicated logical changes, signatures, and focused behavior before using it as the next base. On interruption, inspect current refs and sequencer state; resume from the last verified layer, not from the original list position.
