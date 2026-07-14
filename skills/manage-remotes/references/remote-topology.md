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
which local remote-tracking refs will stop updating or be removed.

A successful fetch proves only that advertised objects/refs were transferred according to the
refspec; it does not prove the current branch is integrated or safe to push.
