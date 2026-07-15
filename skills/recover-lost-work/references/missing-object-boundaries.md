# Missing-object routing boundaries

- **Unreachable but present:** use `recover-lost-work` and create an additive ref.
- **Intentionally omitted by shallow/partial clone and fetchable:** materialize/deepen under `repair-repository-integrity` when correctness is blocked; use setup/optimization only when changing intentional policy.
- **Promised but unavailable, broken shallow metadata, corrupt pack/ref/object:** use `repair-repository-integrity`.
- **Valid LFS pointer with missing LFS payload:** use `manage-large-files`.
- **Missing object inside a submodule repository:** use `manage-submodules`, then repair that exact nested repository if needed.

Do not run prune/repack until the class and recovery source are established.
