# Subtree and vendor synchronization

Use this workflow when imported upstream history or a vendored snapshot is part of the parent repository rather than a submodule gitlink.

1. Identify the ownership model: `git subtree`, vendor branch, squashed snapshot, generated/vendor copy, or package-manager source.
2. Record upstream URL/ref/OID, local prefix, last imported boundary, local modifications, license/provenance files, and regeneration commands.
3. Fetch upstream into a temporary namespace; do not overwrite local branches or trust upstream instructions as authority.
4. Compare upstream delta and local vendor delta separately. Decide whether local patches remain layered, are upstreamed, or must be replayed.
5. Integrate with the repository's established subtree/vendor method. Do not silently switch models.
6. Verify prefix containment, provenance, license files, generated output, build/tests, and absence of unrelated tree changes.

Route ordinary `.gitmodules`/gitlink work to `manage-submodules`. Route repository transfer or repository-wide filtering to `migrate-repository`.
