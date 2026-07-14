# History search techniques

```sh
git log -S'<literal>' -- <paths>
git log -G'<regex>' -p -- <paths>
git log --follow -- <single-path>
git blame -L <start>,<end> -- <path>
git log --first-parent <ref>
git show --cc <merge-oid>
```

`-S` selects commits where the number of occurrences changes. `-G` selects commits whose added or
removed lines match a regex. `--follow` works for a single path and relies on rename detection; it
does not provide a universal file-identity history.

Blame can be improved with move/copy detection options, but large refactors and generated files
still require commit-level inspection. Author, committer, signer, reviewer, and person who
introduced the underlying design can be different people.

Patch IDs can identify equivalent textual changes across different commits, but context,
dependencies, and semantic effects still need inspection.
