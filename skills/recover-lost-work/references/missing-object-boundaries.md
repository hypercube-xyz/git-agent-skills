# Missing-object routing boundaries

Read this when an expected commit, blob, tree, submodule, or LFS payload cannot be read. Record the exact object/path and whether failure is local, nested, or external before selecting a recovery owner.

| Evidence | Owner and limit |
|---|---|
| Object exists but no named ref reaches it | `recover-lost-work`: validate content and add a retaining ref or new path. |
| Object was intentionally omitted by shallow/partial clone | `repair-repository-integrity` when required correctness is blocked; materialize/deepen from a verified source. |
| Promised object unavailable, broken shallow metadata, corrupt ref/pack/object | `repair-repository-integrity`: preserve evidence and reconstruct or repair exact state. |
| Git blob is a valid LFS pointer but payload is missing | `manage-large-files`: verify pointer OID and LFS source. |
| Missing commit is inside a submodule repository | `manage-submodules` owns the relationship; repair the exact nested repository if its object model is damaged. |

A failed read in a partial clone can trigger implicit lazy fetch; disable it for local-only classification. A clean `git fsck` may accept promised missing objects, so it is not proof of offline completeness. Do not prune, repack, reset, or replace a clone until the class, local-only state, and recovery source are established.
