"""One independently installed skill per native Git task; no catalog or sibling skills.

Some diagnostic skills intentionally perform read-only work. Outcome files are explicitly
requested; original index/refs/bytes remain protected. This is one bounded task per skill.
"""
from __future__ import annotations

import json
from pathlib import Path

import fixtures
import run as execution
from smoke_test_git import git, init, commit_file

CORE = {"selected-commit": "craft-commits", "diagnosis": "diagnose-repository", "recovery": "recover-lost-work",
        "stack": "manage-stacked-branches", "publish": "sync-branches", "conflict": "resolve-conflicts",
        "dirty-branch": "manage-branches", "symbolic-tag": "manage-tags", "unborn": "undo-changes",
        "oracle-failure": "find-regression"}
EXTRA = {name: name for name in ("configure-git", "edit-commit-history", "investigate-history", "manage-large-files",
         "manage-remotes", "manage-submodules", "manage-worktrees", "migrate-repository", "optimize-large-repository",
         "preserve-work", "repair-repository-integrity", "setup-repository", "transplant-commits", "integrate-branches")}
OWNERS = CORE | EXTRA


def write(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def create(root):
    fixtures.create(root)
    expected = json.loads((root / "expected.json").read_text(encoding="utf-8"))
    for name in EXTRA:
        p = root / name
        init(p)
        git(p, "branch", "-M", "main")
        old = commit_file(p, "app.txt", "base\n", "base")
        (p / "private.txt").write_bytes(b"retain draft\r\n")
        expected[name] = {"old": old, "index": (p / ".git/index").read_bytes().hex()}
        if name == "manage-remotes":
            expected[name]["endpoint"] = str(root / "unused-archive.git")
        if name in {"edit-commit-history", "investigate-history", "repair-repository-integrity"}:
            newer = commit_file(p, "app.txt", "base\nsecond\n", "second")
            expected[name].update(newer=newer, index=(p / ".git/index").read_bytes().hex())
        if name in {"integrate-branches", "transplant-commits"}:
            git(p, "switch", "-c", "feature")
            selected = commit_file(p, "feature.txt", "feature\n", "feature")
            expected[name]["selected"] = selected
            git(p, "switch", "main")
        if name in {"setup-repository", "migrate-repository", "manage-submodules", "repair-repository-integrity"}:
            source = root / f"{name}-source.git"
            git(root, "clone", "--bare", "--no-local", str(p), str(source))
            expected[name]["source"] = str(source)
        if name == "repair-repository-integrity":
            blob = git(p, "rev-parse", "HEAD:app.txt").stdout.strip()
            object_path = p / ".git/objects" / blob[:2] / blob[2:]
            assert object_path.resolve().is_relative_to((p / ".git/objects").resolve())
            object_path.chmod(0o600)  # Git loose objects are read-only on Windows.
            object_path.unlink()
            expected[name]["blob"] = blob
        if name == "preserve-work":
            (p / "app.txt").write_bytes(b"changed\n")
            git(p, "add", "app.txt")
            expected[name]["index"] = (p / ".git/index").read_bytes().hex()
    write(root / "expected.json", expected)
    return expected


def requests(expected):
    result = {key: value for key, value in execution.requests(expected).items() if key in CORE}
    result.update({
        "configure-git": "Set only this repository's user.name to Standalone Tester and user.email to standalone@example.invalid. Preserve files and refs; do not change global configuration.",
        "edit-commit-history": "Reword the older of these two unpublished commits from 'base' to 'initial base', keeping its original patch and the later commit's patch/message/order. No publication; retain private.txt and the current checkout content.",
        "investigate-history": "Find the commit that introduced the 'second' line in app.txt. Write observations.json containing {commit: full_oid}. Read-only Git inspection; preserve index, refs and all original bytes.",
        "manage-large-files": "Inspect app.txt to determine whether its committed contents are a Git LFS pointer. Write observations.json containing {is_lfs_pointer: boolean}. Do not install LFS, change tracking or migrate history; retain original state.",
        "manage-remotes": f"Add one local remote named archive with URL {expected['manage-remotes']['endpoint']}. Do not fetch or publish. Preserve refs and files.",
        "manage-submodules": f"Add {expected['manage-submodules']['source']} as a submodule at vendor; stage its gitlink and .gitmodules but do not commit. This local file transport within the fixture is authorized. Preserve private.txt.",
        "manage-worktrees": "Create a linked detached worktree at sibling path standalone-linked, at this repository's current HEAD. Preserve all branch refs, original checkout, index and private.txt.",
        "migrate-repository": f"Mirror the refs and objects from the healthy local repository {expected['migrate-repository']['source']} into a new bare repository at sibling path standalone-mirror.git. Both are disposable local paths; do not delete or modify the source or this checkout.",
        "optimize-large-repository": "Measure one read-only status inspection in this small repository. Write observations.json containing {status_seconds: nonnegative_number, changed_configuration: false}. Do not change config, objects or maintenance settings without evidence of a bottleneck; preserve index/refs/bytes.",
        "preserve-work": "Preserve the staged app.txt change and untracked private.txt in a named stash 'standalone-save', leaving a clean worktree and unchanged HEAD. No ignored files or publication are in scope. Verify both files are recoverable in the stash.",
        "repair-repository-integrity": f"The current repository is missing an object. Repair additively using only the verified healthy local repository {expected['repair-repository-integrity']['source']}; preserve HEAD, index and worktree bytes, do not reset/checkout or delete data. Verify fsck afterward.",
        "setup-repository": f"Clone {expected['setup-repository']['source']} into a new sibling directory standalone-clone. Local transport is authorized. Leave the current repository and private.txt unchanged.",
        "transplant-commits": f"Replay only commit {expected['transplant-commits']['selected']} onto current main. Retain feature branch and private.txt; do not publish.",
        "integrate-branches": "Fast-forward current main to the complete local feature branch if ancestry permits. Retain feature and private.txt. Do not publish or create an extra merge commit.",
    })
    return result


def verify(root, name):
    if name in CORE:
        fixtures.verify_case(root, name)
        return
    p = root / name
    e = json.loads((root / "expected.json").read_text(encoding="utf-8"))[name]
    if name != "preserve-work":
        assert (p / "private.txt").read_bytes() == b"retain draft\r\n"
    if name not in {"edit-commit-history", "transplant-commits", "integrate-branches"}:
        assert git(p, "rev-parse", "HEAD").stdout.strip() == e.get("newer", e["old"])
    if name in {"investigate-history", "manage-large-files", "optimize-large-repository", "repair-repository-integrity", "configure-git", "manage-remotes", "setup-repository", "migrate-repository", "manage-worktrees"}:
        assert (p / ".git/index").read_bytes().hex() == e["index"]
    if name == "configure-git":
        assert git(p, "config", "--local", "user.name").stdout.strip() == "Standalone Tester"
        assert git(p, "config", "--local", "user.email").stdout.strip() == "standalone@example.invalid"
    elif name == "edit-commit-history":
        assert git(p, "rev-list", "--count", "HEAD").stdout.strip() == "2"
        assert git(p, "log", "--format=%s", "--reverse").stdout.splitlines() == ["initial base", "second"]
        assert git(p, "show", "HEAD^:app.txt").stdout == "base\n"
        assert git(p, "show", "HEAD:app.txt").stdout == "base\nsecond\n"
    elif name == "investigate-history":
        assert json.loads((p / "observations.json").read_text(encoding="utf-8-sig"))["commit"] == e["newer"]
    elif name == "manage-large-files":
        assert json.loads((p / "observations.json").read_text(encoding="utf-8-sig"))["is_lfs_pointer"] is False
    elif name == "manage-remotes":
        assert git(p, "remote", "get-url", "archive").stdout.strip() == e["endpoint"]
    elif name == "manage-submodules":
        entry = git(p, "ls-files", "--stage", "vendor").stdout.split()
        assert entry[:2] == ["160000", e["old"]]
        assert git(p, "show", ":.gitmodules").stdout
        assert git(p / "vendor", "rev-parse", "HEAD").stdout.strip() == e["old"]
    elif name == "manage-worktrees":
        assert git(root / "standalone-linked", "rev-parse", "HEAD").stdout.strip() == e["old"]
        assert git(root / "standalone-linked", "symbolic-ref", "HEAD", check=False).returncode
    elif name == "migrate-repository":
        target = root / "standalone-mirror.git"
        assert git(target, "rev-parse", "--is-bare-repository").stdout.strip() == "true"
        assert git(target, "show-ref").stdout == git(Path(e["source"]), "show-ref").stdout
        git(target, "fsck", "--full")
    elif name == "optimize-large-repository":
        record = json.loads((p / "observations.json").read_text(encoding="utf-8-sig"))
        assert isinstance(record["status_seconds"], (int, float)) and not isinstance(record["status_seconds"], bool) and record["status_seconds"] >= 0
        assert record["changed_configuration"] is False
    elif name == "preserve-work":
        assert not git(p, "status", "--porcelain").stdout
        assert git(p, "show", "stash@{0}:app.txt").stdout == "changed\n"
        assert git(p, "show", "stash@{0}^2:app.txt").stdout == "changed\n"
        assert git(p, "show", "stash@{0}^3:private.txt").stdout == "retain draft\n"
        assert "standalone-save" in git(p, "stash", "list").stdout
    elif name == "repair-repository-integrity":
        assert git(p, "cat-file", "-p", e["blob"]).stdout == "base\nsecond\n"
        git(p, "fsck", "--full")
    elif name == "setup-repository":
        assert git(root / "standalone-clone", "rev-parse", "HEAD").stdout.strip() == e["old"]
    elif name in {"integrate-branches", "transplant-commits"}:
        assert git(p, "show", "HEAD:feature.txt").stdout == "feature\n"
        assert git(p, "rev-parse", "HEAD^").stdout.strip() == e["old"]
        assert git(p, "rev-parse", "feature").stdout.strip() == e["selected"]
        if name == "integrate-branches":
            assert git(p, "rev-parse", "HEAD").stdout.strip() == e["selected"]
