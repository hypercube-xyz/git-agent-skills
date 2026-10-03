# History editing: sequenced and published rewrites

Read this only when an existing commit series will change. Record `old_base`, `old_tip`, the selected commit OIDs, intended order/content, and every ref or review consumer before invoking a sequencer. Make a recovery ref outside `refs/heads/` at `old_tip`; verify its OID and ensure `rebase.updateRefs` cannot move it.

## Choose the local operation

- Reword/fixup/squash/reorder: inspect the complete interactive todo before execution. A dropped line removes a commit; a fixup changes descendants even when the final file tree looks identical.
- Split/edit: stop at the intended commit, reset only the selected commit into the index/worktree under an explicit retention policy, create the replacement commits, and continue. Verify no unrelated edits entered either commit.
- Rebase onto a new base: distinguish moving the entire branch from rewriting only a selected suffix. For the latter, identify the exact upstream boundary before using `rebase --onto`; a wrong boundary duplicates or drops commits.
- Merge commits: ordinary interactive rebase may flatten topology. Use a reviewed merge-preserving plan only when required, then inspect every reconstructed parent relation.
- Signatures: rewritten commits are new objects. Verify required signatures anew; do not infer validity from their predecessors.

Compare `git range-diff old_base..old_tip new_base..new_tip` for patch intent, then separately compare final trees, graph, messages, signatures, notes/tags, and affected tests. A matching range-diff cannot prove merge ancestry or final behavior.

## Published replacement

Before publication, expose a checkpoint with old/new tip OIDs, exact range, destination account and effective push endpoint, destination ref and current OID, consumers, recovery ref, and verification. Query the push endpoint close to action; a fetch remote-tracking ref may be stale or point elsewhere. Use a single explicit refspec with `--no-follow-tags` and `--force-with-lease=<ref>:<observed-oid>`; never an implicit lease or broad force.

After timeout or nonzero exit, query the same endpoint/ref before retrying. If the ref equals the intended OID, verify downstream result; if it equals the expected old OID, a bounded retry may be safe; any third value invalidates the plan. Keep the recovery ref until affected consumers accept the replacement.
