# Branch divergence and publication

Read this after resolving the exact local branch, upstream mapping, effective fetch/push endpoints, and destination ref. A remote-tracking ref is a local snapshot. Fetch the selected branch or query the exact endpoint before a claim about current remote state; a query alone does not provide objects for ancestry tests.

| Observed relationship | Choice when it matches the task |
|---|---|
| Equal tips | Verify tracking metadata; no history operation. |
| Local tip ancestor of remote tip | Fast-forward locally with the verified remote commit; preserve conflicting work first. |
| Remote tip ancestor of local tip | Ordinary explicit push may publish a fast-forward update. |
| Neither tip ancestor | Ask or use established policy for merge versus permitted rebase; local integration belongs to `integrate-branches`. |
| Remote destination absent | Treat as explicit branch creation; a missing old OID is not proof of a fast-forward. |
| Local branch unborn | Establish the first commit and target mapping separately; no ahead/behind arithmetic exists. |

For divergence, inspect commits and merge base from both sides; `git pull` defaults cannot choose the user's topology. A rebase requires evidence that rewritten commits are not shared. After integration, re-read local state and remote endpoint before publication.

A push through a named remote may update local remote-tracking refs from its advertised result. When fetch and push endpoints differ, this can make a local tracking ref reflect the push destination while the fetch repository remains at another OID. Record each observation's endpoint and, when the fetch-side state matters afterward, query or bounded-fetch the selected fetch ref again; do not report the fetch side synchronized from the tracking ref alone.

For a push, use one explicit source OID/ref and destination `refs/heads/<name>` with `--no-follow-tags` unless tags are in scope. For an existing destination, prove the observed remote tip is an ancestor of the proposed tip; the server's ordinary non-force push still protects against concurrent movement. Query the push endpoint/ref afterward. On timeout, query first, then decide whether any retry is needed.

For a fork contribution, verify upstream as the base source and the fork as push destination, including URL rewrites and `pushRemote`; never infer the destination from the name `origin`. The contribution branch's base and published fork ref are separate postconditions.
