# Subtree and vendor synchronization

Read this when upstream content is imported into the superproject tree rather than recorded as a submodule gitlink. Establish whether the repository uses `git subtree`, a vendor branch, squash snapshots, generated copies, or package-manager sources. Preserve that model unless a change is explicitly requested.

1. Record upstream URL/ref/OID, local prefix, last imported boundary, local modifications, license/provenance files, and regeneration commands. A directory named `vendor` does not by itself reveal its source or import method.
2. Fetch upstream into an isolated temporary namespace after verifying endpoint and scope. For a parent-only import observation, use `--no-tags --no-recurse-submodules --no-prune --no-prune-tags` and an explicit destination; use `--refmap=` with a named remote when its configured mappings are outside scope. An exact refspec alone can still update tags, nested repositories, or additional tracking refs. Verify the complete changed local ref set before comparing upstream changes and local vendor patches; detect already imported content by history or patch/content equivalence. Authorize required tags or nested data separately. Inspect automatic maintenance/commit-graph settings and suppress their incidental writes where protected recovery or object state requires it.
3. Choose the repository's established subtree/vendor operation. A subtree split/merge, squash import, and copied snapshot produce different ancestry; do not substitute one merely because it gives a clean diff.
4. If local patches exist, decide from evidence whether they remain layered, were upstreamed, or need replay. A mechanical overwrite can erase them even when the upstream import succeeds.
5. Verify the prefix contains exactly the intended upstream delta plus retained local changes. Review provenance/license files, generated output, build/tests, and unrelated tree paths. Verify the stored upstream OID or snapshot marker when the repository uses one.

If the path is mode 160000, route the gitlink and nested checkout to `manage-submodules`. Whole-repository transfer or filtering belongs to `migrate-repository`.
