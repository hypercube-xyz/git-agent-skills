# Large-repository performance map

| Bottleneck | Candidate mechanisms |
|---|---|
| Worktree population/status | sparse checkout, sparse index, filesystem monitor where supported |
| Initial blob transfer | partial clone (`blob:none` or justified filter) |
| History transfer | shallow clone only when ancestry limitations are acceptable |
| Repeated graph walks | commit-graph and changed-path Bloom filters |
| Many packs | multi-pack-index and incremental repack |
| Routine housekeeping | `git maintenance` / Scalar-style scheduling |

Use trace facilities such as `GIT_TRACE2_PERF` where appropriate and avoid collecting sensitive
paths or URLs in shared logs.

Sparse checkout can set skip-worktree bits; do not manually clear them as a generic repair. Partial
clone depends on a promisor remote and may trigger on-demand network access. Prune expiry is a
recovery policy, not merely a performance knob.
