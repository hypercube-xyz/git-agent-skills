# Bisect oracle design

A good oracle is:

- deterministic enough to repeat,
- scoped to the behavior in question,
- self-contained for historical revisions,
- explicit about good, bad, skip, and infrastructure failure,
- bounded by time/resource limits,
- cleaned between candidates.

For `git bisect run`, reserve exit 125 for untestable revisions. Do not map missing dependencies,
network outages, unsupported toolchains, or timeouts to “bad” unless those conditions are the
regression being investigated.

Trial the script at both endpoints before the search. Store logs outside tracked paths or in a
disposable worktree/clone. After the candidate is found, rerun the oracle multiple times at the
candidate and relevant parent, then inspect the diff for a plausible causal mechanism.
