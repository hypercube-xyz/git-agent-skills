# Partial clone and sparse checkout for performance

Read this only when changing intentional policy in a healthy repository. A missing required object or broken promisor/shallow metadata belongs to integrity repair.

- Sparse checkout chooses worktree paths; inspect cone mode, sparse patterns, sparse-index support, and worktree-specific config. Before narrowing patterns, inventory untracked and ignored files under excluded directories: Git may delete ignored files there, and widening later restores only tracked files.
- Partial clone filters choose omitted object content; inspect `extensions.partialClone`, promisor remote, filter specification, server support, and tools that assume offline blobs. A local `show` or `diff` may trigger lazy network retrieval unless disabled for observation.
- Shallow history chooses an ancestry boundary. It does not replace a blob filter and can make merge-base, blame, or bisect questions inconclusive.
- Apply one mechanism tied to the measured bottleneck, feature-detect support, and record the before/after workload with comparable cache/network conditions.
- Materialize objects needed for representative offline build/test/checkout paths before disconnecting. A successful online check cannot prove offline completeness.
- Verify required files, commits, command behavior, storage/transfer measurements, and unaffected worktrees. If benefit is small or compatibility cost is high, return to the prior policy rather than stacking more mechanisms.
