# Integration strategies

## Default decision

1. If destination is an ancestor of source and policy permits, fast-forward.
2. If preserving published topology or explicit integration context matters, merge.
3. If only unpublished local commits need a clean new base and policy permits rewrite, rebase.
4. If the task selects individual commits rather than a whole line, use `transplant-commits`.

Always inspect the merge base and the commit set on each side. A clean textual application does not
prove semantic compatibility.

## Recovery anchors

Record original source/destination OIDs. During rebase, understand that `ours` and `theirs` are
presented from the operation's perspective and may feel inverted relative to a normal merge.
`ORIG_HEAD` and reflogs can help recovery but are not substitutes for an explicit recorded OID.

Octopus, subtree, unrelated histories, and criss-cross merges require an explicit reason and
stronger verification; do not select them as generic fixes.
