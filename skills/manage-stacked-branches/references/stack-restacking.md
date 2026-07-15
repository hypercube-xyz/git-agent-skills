# Stack restacking

Model branches as a DAG of exact tip and intended-parent OIDs. Record old per-layer ranges/diffs and recovery refs. Detect parent commits that landed by merge, rebase, or squash using ancestry plus patch/content equivalence. Restack bottom-up, verify each layer before using it as the next base, and review reused conflict resolutions. A layer may become empty only when its full intended change is established on the new parent.
