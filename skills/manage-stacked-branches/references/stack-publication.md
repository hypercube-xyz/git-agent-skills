# Publishing a rewritten stack

Read this when several dependent refs may change remotely. Prepare a table per ref: old local OID, intended new OID, exact remote ref, observed remote OID or absence, effective push endpoint, branch policy, and recovery ref. Include only refs whose change is authorized; `--no-follow-tags` avoids incidental tag publication.

## Choose transaction shape

- If every ref must change together, verify server support for `git push --atomic` and use explicit refspecs plus one exact `--force-with-lease=<ref>:<observed-oid>` per rewritten ref.
- If partial publication is acceptable, choose an order that leaves reviewers a usable parent chain, and state how each intermediate remote state can be recovered.
- A new remote ref has no old commit for ancestry. Treat creation separately and detect a concurrent creation before retry.
- Multiple push URLs mean multiple destinations. Either authorize and verify each, or address one verified endpoint explicitly.

Immediately before push, refresh every destination ref at the same endpoint used for publication. A moved ref or changed protection invalidates the whole coordinated plan. After push or timeout, query all destination refs independently; classify each as intended, old/absent, changed by another actor, or unknown. Retry only effects proven absent under still-valid scope. Do not call a partial set successful, and do not force a rollback over new concurrent work.
