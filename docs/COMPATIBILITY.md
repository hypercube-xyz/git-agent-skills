# Compatibility

## Environment

- Python: 3.9 or newer for bundled scripts.
- Git: 2.35 or newer. Workflows feature-detect commands and options when behavior varies by version.
- Packaging clients tested in the upstream validation record: Skills CLI 1.5.17 and Claude Code
  2.1.209.
- CI operating system: Ubuntu.

## Feature detection

Before relying on sparse index, partial clone filters, maintenance, worktree porcelain options, or
exact push modes:

1. inspect `git --version` and the relevant command help or capability;
2. use the native feature when available;
3. use a fallback only when it preserves the same postcondition and safety properties;
4. otherwise stop and report the unsupported operation.

Provider authentication, branch protection, hosted releases, and remote policy require
provider-specific tests.
