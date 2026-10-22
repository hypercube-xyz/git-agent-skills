# Compatibility

## Environment

- Python: 3.14 for bundled scripts. CI runs the validators and semantic suite on Python 3.14.
- Git: 2.35 or newer is the declared compatibility target. Optional commands and modes are
  feature-detected; the exact Git version used for a release build is recorded in the release metadata file.
  A blocking reusable CI job builds checksum-pinned Git 2.35.0 and runs the local semantic,
  security, review and recheck suites. Platform jobs also exercise the Git supplied by each runner.
  The minimum-version build omits HTTP/TLS transports; it proves local command mechanics,
  not hosted authentication or transport compatibility.
- CI operating systems: `ubuntu-latest`, `macos-latest`, and `windows-latest` GitHub-hosted runner
  images. The full semantic suite runs on Linux; macOS and Windows run a platform-appropriate subset.
  The release is built on `ubuntu-latest`.
- Blocking packaging-client checks use Node 24, Skills CLI 1.5.17, and Claude Code 2.1.209.
  A non-blocking Node 26 probe exercises the latest available client releases on pushes to `main`
  and manual workflow runs.

## Version 2 migration

The 24 skill names and paths are unchanged. Their instruction structure and decision rules changed, so consumers that parse headings or prose must review those integrations. The remote inspection helper retains its configured remote fields and adds effective endpoint observations; callers should treat its display fields as potentially sensitive.

## Feature detection

Before relying on sparse index, partial clone filters, maintenance, worktree porcelain options,
atomic push, or exact push modes:

1. inspect `git --version` and the relevant command help or advertised capability;
2. use the native feature when available;
3. use a fallback only when it preserves the same postcondition and safety properties;
4. otherwise stop and report the unsupported operation.

Provider authentication, branch protection, hosted releases, and remote policy require
provider-specific tests.

The review suite reports `supported`, `safe_refusal`, `unsupported`, and `failed` separately.
A safe refusal means the requested optional operation is unavailable and the verified
stop path preserves protected state; it does not mean the operation completed. For example,
Git 2.35.0 cannot perform symbolic-target compare-and-swap transactions. Unexpected skips
are classified as unsupported and make the direct review-suite command fail.

The [2026-10-18 local Git 2.35.0 logs](../tests/compatibility/git-2.35.0/environment.json)
record 49 supported smoke cases, one safe refusal for NUL worktree inventory, and
21 supported review cases plus one symbolic-target transaction refusal, with zero
unsupported skips. That run used Ubuntu/WSL and Python 3.12.3; the CI job uses Python
3.14. These local logs do not assert a GitHub Actions run result.
