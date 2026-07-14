# Remote topology

Use the bundled helper before reporting configured remotes:

```sh
python3 skills/manage-remotes/scripts/inspect_remotes.py
```

The helper is intentionally fail-closed: unknown or opaque address forms are redacted rather than
echoed. Python 3.9+ is required. If it is unavailable, do not print remote URLs; report names and
request a safe runtime path instead.

## Distinguish the layers

- `remote.<name>.url`: fetch destination.
- `remote.<name>.pushurl`: optional push-only destination.
- `remote.<name>.fetch`: mapping from remote refs to local remote-tracking refs.
- `url.*.insteadOf` / `pushInsteadOf`: rewrites that can change the effective destination.
- `refs/remotes/<name>/*`: local observations, not the remote's live state.

Before pruning, enumerate the complete dry-run candidate set. Before changing a refspec, identify
which local remote-tracking refs will stop updating or be removed. A refspec such as
`refs/tags/*:refs/tags/*` maps into a shared local namespace; pruning through it can remove tags
that originated from another remote or were created locally, so establish provenance for every
candidate.

A successful fetch proves only that advertised objects/refs were transferred according to the
refspec; it does not prove the current branch is integrated or safe to push.

## Path and output safety

When paths or ref names can be user-controlled, pass command arguments as arrays rather than shell-concatenated strings, use `--` before pathspecs, and use NUL-delimited output (`-z`) for machine parsing. Do not split filenames on whitespace or newlines. Test names beginning with `-`, whitespace/newlines, Unicode, symlinks, nested repositories, and case-collision scenarios where the platform permits them.
