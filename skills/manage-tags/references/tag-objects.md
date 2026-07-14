# Tag object verification

Inspect both ref and object:

```sh
git show-ref --verify refs/tags/<name>
git cat-file -t refs/tags/<name>
git rev-parse refs/tags/<name>
git rev-parse refs/tags/<name>^{}
git for-each-ref --format='%(refname) %(objecttype) %(objectname) %(*objecttype) %(*objectname)' refs/tags/<name>
```

A lightweight tag ref points directly to the target. An annotated/signed tag points to a tag object
that records target, type, tag name, tagger, message, and optional signature.

Signature verification proves a cryptographic relationship to a key under the verifier's trust
configuration; it does not by itself prove release correctness or authorization.

Never use broad `git push --tags` when the task names one tag. Push an exact
`refs/tags/<name>:refs/tags/<name>` mapping after destination verification.
