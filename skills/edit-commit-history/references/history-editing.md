# History editing

Freeze exact old tip/base OIDs and the intended series contract. Create a recovery ref. Use the smallest rewrite primitive, review sequence changes and patch equivalence, and run focused tests. Published rewrite requires a current remote OID, exact `--force-with-lease=<ref>:<oid>`, verified destination, and remote postcondition checks.

Before a risky rewrite, inspect the target branch, working state, publication status, adjacent worktrees, and protected work. Create and verify rescue state before rewriting. Refresh the remote OID immediately before publication and present the material consequence, recovery path, and exact destination. `edit-commit-history` owns an approved leased publication of the rewritten series; `sync-branches` must not independently force-update the same ref.

Multi-branch dependency graphs belong to `manage-stacked-branches`; repository-wide filtering belongs only to an explicitly scoped migration workflow.
