# Stack publication

Immediately before publication, fetch every destination ref and record exact expected OIDs. Prepare explicit `<local>:<remote>` refspecs and one exact lease per rewritten ref. Verify branch protection and whether the server supports atomic push. Use atomic publication only when all refs must change together; otherwise define an order and recovery state. After any ambiguous or partial result, query every ref independently and stop before retrying.

The stack owner retains the branch DAG, recovery refs, bottom-up restack, per-layer diff verification, and coordinated publication plan. `resolve-conflicts` may support one stopped layer, and `sync-branches` may provide bounded single-ref evidence, but neither independently publishes the stack. Stop on a moved parent, ambiguous squash equivalence, policy change, or partial publication.
