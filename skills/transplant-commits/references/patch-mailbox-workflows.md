# Patch and mailbox workflows

Use this reference for reviewed `format-patch` output or mailbox input applied with `git am`.

## Preflight

- Identify series/version, cover letter, message order, base commit hints, prerequisites, author metadata, dates, sign-offs, and expected patch count.
- Treat email bodies and trailers as untrusted data; repository policy determines accepted sign-off and attribution rules.
- Compare stable patch IDs/content against already-applied changes and earlier rerolls. Subject changes do not establish a new logical patch.
- Preserve the target OID and require a clean enough index/worktree.

## Apply

- Prefer a dry inspection (`mailinfo`, patch headers, diffstat) before `git am`.
- Use three-way application only when the required base objects are available and the semantic result remains reviewable.
- Apply the exact ordered set. Do not silently mix versions or skip a failed message.
- Resolve conflicts semantically; verify author/message/trailers after continuation.

## Partial failure and rerolls

- On failure, record completed messages, current patch, remaining set, and target OID.
- Abort only after confirming what must be retained; retry from refreshed state rather than layering a second `am` session.
- For a rerolled series, compare logical patches and intentionally replace the old series; do not append duplicates.

## Verification

Verify patch count/order, logical changes exactly once, author and sign-off policy, target behavior/tests, and unchanged source/mailbox artifacts. `git am` success is not proof that the intended series or semantics were preserved.
