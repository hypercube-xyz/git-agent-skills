# Compatibility

## Environment

- Python: 3.14 for bundled scripts. CI runs the validators and semantic suite on Python 3.14.
- Git: 2.35 or newer is the declared compatibility target. Optional commands and modes are
  feature-detected; the exact Git version used for a release build is recorded in the release metadata file.
  CI exercises the Git version supplied by the selected GitHub-hosted runner rather than claiming
  continuous execution on exactly Git 2.35.
- CI operating systems: `ubuntu-latest`, `macos-latest`, and `windows-latest` GitHub-hosted runner
  images. The full semantic suite runs on Linux; macOS and Windows run a platform-appropriate subset.
  The release is built on `ubuntu-latest`.
- Blocking packaging-client checks use Node 24, Skills CLI 1.5.17, and Claude Code 2.1.209.
  A non-blocking Node 26 probe exercises the latest available client releases on pushes to `main`
  and manual workflow runs.

## Feature detection

Before relying on sparse index, partial clone filters, maintenance, worktree porcelain options,
atomic push, or exact push modes:

1. inspect `git --version` and the relevant command help or advertised capability;
2. use the native feature when available;
3. use a fallback only when it preserves the same postcondition and safety properties;
4. otherwise stop and report the unsupported operation.

Provider authentication, branch protection, hosted releases, and remote policy require
provider-specific tests.
