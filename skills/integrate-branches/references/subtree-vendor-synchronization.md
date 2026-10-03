# Subtree and vendor synchronization

Read this when upstream content is imported into the superproject tree rather than recorded as a submodule gitlink. Establish whether the repository uses `git subtree`, a vendor branch, squash snapshots, generated copies, or package-manager sources. Preserve that model unless a change is explicitly requested.

1. Record upstream URL/ref/OID, local prefix, last imported boundary, local modifications, license/provenance files, and regeneration commands. A directory named `vendor` does not by itself reveal its source or import method.
2. Fetch upstream into an isolated temporary namespace after verifying endpoint and scope. Compare upstream changes and local vendor patches separately; detect already imported content by history or patch/content equivalence.
3. Choose the repository's established subtree/vendor operation. A subtree split/merge, squash import, and copied snapshot produce different ancestry; do not substitute one merely because it gives a clean diff.
4. If local patches exist, decide from evidence whether they remain layered, were upstreamed, or need replay. A mechanical overwrite can erase them even when the upstream import succeeds.
5. Verify the prefix contains exactly the intended upstream delta plus retained local changes. Review provenance/license files, generated output, build/tests, and unrelated tree paths. Verify the stored upstream OID or snapshot marker when the repository uses one.

If the path is mode 160000, route the gitlink and nested checkout to `manage-submodules`. Whole-repository transfer or filtering belongs to `migrate-repository`.
