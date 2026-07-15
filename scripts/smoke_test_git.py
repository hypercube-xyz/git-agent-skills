#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

sys.dont_write_bytecode = True


class TestRunner:
    def __init__(self):
        self.ok = 0
        self.skip = 0

    def run(self, name: str, fn: Callable[[], None]) -> None:
        try:
            fn()
            self.ok += 1
            print("PASS", name)
        except SkipTest as exc:
            self.skip += 1
            print("SKIP", name, "-", exc)
        except Exception as exc:
            print("FAIL", name, "-", exc)
            raise


class SkipTest(Exception):
    pass


def git(cwd, *args, check=True, env=None):
    cp = subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, env=env
    )
    if check and cp.returncode:
        raise RuntimeError(f"git {args}: {cp.stderr or cp.stdout}")
    return cp


def init(p):
    p.mkdir(parents=True)
    git(p, "init", "-q")
    git(p, "config", "user.name", "Test User")
    git(p, "config", "user.email", "test@example.invalid")


def commit_file(p, name, content, msg):
    (p / name).parent.mkdir(parents=True, exist_ok=True)
    (p / name).write_text(content)
    git(p, "add", "--", name)
    git(p, "commit", "-q", "-m", msg)
    return git(p, "rev-parse", "HEAD").stdout.strip()


def test_mailbox(td):
    src = td / "src"
    dst = td / "dst"
    init(src)
    base = commit_file(src, "f", "base\n", "base")
    commit_file(src, "f", "base\none\n", "one")
    commit_file(src, "g", "two\n", "two")
    patches = td / "patches"
    patches.mkdir()
    git(src, "format-patch", "-q", "-o", str(patches), f"{base}..HEAD")
    init(dst)
    commit_file(dst, "f", "base\n", "base")
    files = sorted(str(x) for x in patches.glob("*.patch"))
    git(dst, "am", *files)
    assert (dst / "f").read_text() == "base\none\n" and (
        dst / "g"
    ).read_text() == "two\n"
    assert len(git(dst, "rev-list", "--count", "HEAD").stdout.strip()) > 0


def test_shallow(td):
    src = td / "src"
    init(src)
    for i in range(5):
        commit_file(src, "f", f"{i}\n", f"c{i}")
    clone = td / "clone"
    git(td, "clone", "-q", "--depth", "1", f"file://{src}", str(clone))
    assert git(clone, "rev-parse", "--is-shallow-repository").stdout.strip() == "true"
    git(clone, "fetch", "-q", "--deepen", "10")
    assert git(clone, "rev-parse", "--is-shallow-repository").stdout.strip() == "false"


def test_corruption_detection(td):
    p = td / "repo"
    init(p)
    oid = commit_file(p, "data", "payload\n", "data")
    blob = git(p, "rev-parse", "HEAD:data").stdout.strip()
    obj = p / ".git" / "objects" / blob[:2] / blob[2:]
    if not obj.exists():
        raise SkipTest("object packed unexpectedly")
    backup = obj.read_bytes()
    obj.unlink()
    cp = git(p, "fsck", "--full", check=False)
    assert cp.returncode != 0 and blob in (cp.stdout + cp.stderr)
    assert not obj.exists()
    obj.parent.mkdir(exist_ok=True)
    obj.write_bytes(backup)
    git(p, "fsck", "--full")


def test_stack(td):
    p = td / "repo"
    init(p)
    commit_file(p, "base", "0\n", "base")
    git(p, "branch", "A")
    git(p, "switch", "-q", "A")
    commit_file(p, "a", "A\n", "A")
    oldA = git(p, "rev-parse", "HEAD").stdout.strip()
    git(p, "branch", "B")
    git(p, "switch", "-q", "B")
    commit_file(p, "b", "B\n", "B")
    oldB = git(p, "rev-parse", "HEAD").stdout.strip()
    git(p, "branch", "C")
    git(p, "switch", "-q", "C")
    commit_file(p, "c", "C\n", "C")
    git(p, "switch", "-q", "master")
    commit_file(p, "base", "0\nmain\n", "main2")
    newbase = git(p, "rev-parse", "HEAD").stdout.strip()
    git(p, "switch", "-q", "A")
    git(p, "rebase", newbase)
    newA = git(p, "rev-parse", "HEAD").stdout.strip()
    git(p, "switch", "-q", "B")
    git(p, "rebase", "--onto", newA, oldA, "B")
    newB = git(p, "rev-parse", "HEAD").stdout.strip()
    git(p, "switch", "-q", "C")
    git(p, "rebase", "--onto", newB, oldB, "C")
    assert git(p, "merge-base", "--is-ancestor", "A", "B", check=False).returncode == 0
    assert git(p, "merge-base", "--is-ancestor", "B", "C", check=False).returncode == 0
    assert (
        (p / "a").read_text() == "A\n"
        and (p / "b").read_text() == "B\n"
        and (p / "c").read_text() == "C\n"
    )


def test_vendor_branch(td):
    upstream = td / "up"
    init(upstream)
    commit_file(upstream, "lib.txt", "v1\n", "v1")
    up1 = git(upstream, "rev-parse", "HEAD").stdout.strip()
    commit_file(upstream, "lib.txt", "v2\n", "v2")
    up2 = git(upstream, "rev-parse", "HEAD").stdout.strip()
    p = td / "repo"
    init(p)
    commit_file(p, "app", "app\n", "app")
    git(p, "remote", "add", "vendor", str(upstream))
    git(p, "fetch", "-q", "vendor")
    # Import exact snapshot under a prefix, then update only that prefix.
    (p / "vendor").mkdir()
    data = git(upstream, "show", f"{up1}:lib.txt").stdout
    (p / "vendor/lib.txt").write_text(data)
    git(p, "add", "vendor/lib.txt")
    git(p, "commit", "-q", "-m", f"vendor {up1}")
    data = git(upstream, "show", f"{up2}:lib.txt").stdout
    (p / "vendor/lib.txt").write_text(data)
    git(p, "add", "vendor/lib.txt")
    git(p, "commit", "-q", "-m", f"vendor {up2}")
    assert (p / "app").read_text() == "app\n" and (
        p / "vendor/lib.txt"
    ).read_text() == "v2\n"


def test_identity_include(td):
    home = td / "home"
    home.mkdir()
    work = td / "work"
    personal = td / "personal"
    init(work)
    init(personal)
    for repo in (work, personal):
        git(repo, "config", "--local", "--unset", "user.name")
        git(repo, "config", "--local", "--unset", "user.email")
    inc = home / "work.inc"
    inc.write_text(
        "[user]\n\tname = Work User\n\temail = work@example.invalid\n[commit]\n\tgpgSign = false\n"
    )
    main = home / ".gitconfig"
    main.write_text(
        f'[user]\n\tname = Personal User\n\temail = personal@example.invalid\n[includeIf "gitdir:{work}/.git"]\n\tpath = {inc}\n'
    )
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    assert (
        git(work, "config", "user.email", env=env).stdout.strip()
        == "work@example.invalid"
    )
    assert (
        git(personal, "config", "user.email", env=env).stdout.strip()
        == "personal@example.invalid"
    )
    assert (
        str(inc)
        in git(work, "config", "--show-origin", "--get", "user.email", env=env).stdout
    )


def test_actual_subtree(td):
    upstream = td / "upstream"
    init(upstream)
    commit_file(upstream, "lib.txt", "v1\n", "v1")
    parent = td / "parent"
    init(parent)
    commit_file(parent, "app.txt", "app\n", "app")
    cp = git(
        parent,
        "subtree",
        "add",
        "--prefix=vendor/lib",
        str(upstream),
        "master",
        "--squash",
        check=False,
    )
    if cp.returncode != 0:
        raise SkipTest(
            "git subtree unavailable or unsupported: "
            + (cp.stderr or cp.stdout).strip()[:160]
        )
    assert (parent / "vendor/lib/lib.txt").read_text() == "v1\n"
    commit_file(upstream, "lib.txt", "v2\n", "v2")
    git(
        parent,
        "subtree",
        "pull",
        "--prefix=vendor/lib",
        str(upstream),
        "master",
        "--squash",
    )
    assert (parent / "vendor/lib/lib.txt").read_text() == "v2\n"
    assert (parent / "app.txt").read_text() == "app\n"


def test_signing_and_hook(td):
    if shutil.which("gpg") is None:
        raise SkipTest("gpg unavailable")
    p = td / "repo"
    init(p)
    gnupg = td / "gnupg"
    gnupg.mkdir(mode=0o700)
    env = os.environ.copy()
    env["GNUPGHOME"] = str(gnupg)
    cp = subprocess.run(
        [
            "gpg",
            "--batch",
            "--homedir",
            str(gnupg),
            "--passphrase",
            "",
            "--quick-generate-key",
            "Test User <test@example.invalid>",
            "ed25519",
            "sign",
            "0",
        ],
        text=True,
        capture_output=True,
        env=env,
    )
    if cp.returncode:
        raise SkipTest(
            "unable to create disposable GPG key: " + cp.stderr.strip()[:120]
        )
    listing = subprocess.run(
        [
            "gpg",
            "--batch",
            "--homedir",
            str(gnupg),
            "--with-colons",
            "--list-secret-keys",
        ],
        text=True,
        capture_output=True,
        env=env,
        check=True,
    ).stdout
    fpr = next(
        line.split(":")[9] for line in listing.splitlines() if line.startswith("fpr:")
    )
    hooks = td / "hooks"
    hooks.mkdir()
    hook = hooks / "pre-commit"
    hook.write_text("#!/bin/sh\nprintf invoked > .git/hook-marker\n")
    hook.chmod(0o755)
    git(p, "config", "gpg.program", "gpg")
    git(p, "config", "user.signingKey", fpr)
    git(p, "config", "commit.gpgSign", "true")
    git(p, "config", "core.hooksPath", str(hooks))
    (p / "signed.txt").write_text("signed\n")
    git(p, "add", "signed.txt", env=env)
    git(p, "commit", "-q", "-m", "signed commit", env=env)
    assert (p / ".git/hook-marker").read_text() == "invoked"
    git(p, "verify-commit", "HEAD", env=env)


def test_exact_lease(td):
    remote = td / "r.git"
    git(td, "init", "-q", "--bare", str(remote))
    a = td / "a"
    b = td / "b"
    init(a)
    commit_file(a, "f", "0\n", "base")
    git(a, "remote", "add", "origin", str(remote))
    git(a, "push", "-q", "origin", "HEAD:refs/heads/main")
    git(td, "clone", "-q", str(remote), str(b))
    git(b, "config", "user.name", "B")
    git(b, "config", "user.email", "b@example.invalid")
    git(b, "switch", "-q", "main")
    commit_file(b, "f", "0\nb\n", "b")
    git(b, "push", "-q", "origin", "main")
    old = git(a, "rev-parse", "refs/remotes/origin/main").stdout.strip()
    commit_file(a, "g", "a\n", "a")
    cp = git(
        a,
        "push",
        f"--force-with-lease=refs/heads/main:{old}",
        "origin",
        "HEAD:refs/heads/main",
        check=False,
    )
    assert cp.returncode != 0


def test_reflog(td):
    p = td / "repo"
    init(p)
    commit_file(p, "f", "base\n", "base")
    lost = commit_file(p, "f", "base\nlost\n", "lost")
    git(p, "reset", "--hard", "HEAD~1")
    assert git(p, "cat-file", "-e", lost, check=False).returncode == 0
    git(p, "branch", "recovered", lost)
    assert git(p, "rev-parse", "recovered").stdout.strip() == lost


def test_pathological_filename(td):
    p = td / "repo"
    init(p)
    name = "-nasty name\nline"
    (p / name).write_text("x")
    git(p, "add", "--", name)
    git(p, "commit", "-q", "-m", "path")
    out = git(p, "ls-files", "-z").stdout
    assert name + "\0" == out


def test_tag_exact_lease(td):
    remote = td / "r.git"
    git(td, "init", "-q", "--bare", str(remote))
    a = td / "a"
    b = td / "b"
    init(a)
    base = commit_file(a, "f", "0\n", "base")
    git(a, "tag", "-a", "v1", "-m", "v1", base)
    git(a, "remote", "add", "origin", str(remote))
    git(a, "push", "-q", "origin", "HEAD:refs/heads/main", "refs/tags/v1")
    git(td, "clone", "-q", str(remote), str(b))
    git(b, "config", "user.name", "B")
    git(b, "config", "user.email", "b@example.invalid")
    commit_file(b, "b", "b\n", "b")
    git(b, "tag", "-f", "-a", "v1", "-m", "moved")
    old = git(a, "rev-parse", "refs/tags/v1").stdout.strip()
    git(b, "push", "-q", "--force", "origin", "refs/tags/v1")
    git(a, "tag", "-f", "-a", "v1", "-m", "local move", base)
    cp = git(
        a,
        "push",
        f"--force-with-lease=refs/tags/v1:{old}",
        "origin",
        "refs/tags/v1",
        check=False,
    )
    assert cp.returncode != 0


def test_push_post_verification(td):
    r = td / "r.git"
    git(td, "init", "-q", "--bare", str(r))
    p = td / "p"
    init(p)
    oid = commit_file(p, "f", "x\n", "x")
    git(p, "remote", "add", "origin", str(r))
    git(p, "push", "-q", "origin", "HEAD:refs/heads/main")
    advertised = git(
        p, "ls-remote", "--refs", "origin", "refs/heads/main"
    ).stdout.split()[0]
    assert advertised == oid


def test_tag_peeling(td):
    p = td / "r"
    init(p)
    oid = commit_file(p, "f", "x\n", "x")
    git(p, "tag", "-a", "v1", "-m", "annotated", oid)
    tag = git(p, "rev-parse", "v1").stdout.strip()
    peeled = git(p, "rev-parse", "v1^{}").stdout.strip()
    assert tag != peeled and peeled == oid
    assert git(p, "cat-file", "-t", tag).stdout.strip() == "tag"


def test_worktree_nul(td):
    p = td / "r"
    init(p)
    commit_file(p, "f", "x\n", "x")
    wt = td / "work tree\nodd"
    git(p, "worktree", "add", "-q", "-b", "topic", str(wt))
    cp = subprocess.run(
        ["git", "worktree", "list", "--porcelain", "-z"],
        cwd=p,
        stdout=subprocess.PIPE,
        check=True,
    )
    assert b"\0" in cp.stdout and os.fsencode(str(wt)) in cp.stdout


def test_clean_preview(td):
    p = td / "r"
    init(p)
    commit_file(p, "tracked", "x\n", "x")
    (p / "untracked").write_text("u")
    (p / ".ignored").write_text("i")
    (p / ".gitignore").write_text(".ignored\n")
    out = git(p, "clean", "-ndx").stdout
    assert (
        "untracked" in out
        and ".ignored" in out
        and (p / "untracked").exists()
        and (p / ".ignored").exists()
    )


def test_hard_reset_non_obstructing(td):
    p = td / "r"
    init(p)
    commit_file(p, "f", "one\n", "one")
    target = commit_file(p, "f", "two\n", "two")
    (p / "f").write_text("dirty\n")
    (p / "keep.untracked").write_text("keep\n")
    git(p, "reset", "--hard", target)
    assert (p / "f").read_text() == "two\n" and (
        p / "keep.untracked"
    ).read_text() == "keep\n"


def test_hard_reset_obstruction_detected(td):
    p = td / "r"
    init(p)
    first = commit_file(p, "base", "x\n", "base")
    (p / "dir").mkdir()
    (p / "dir/file").write_text("tracked\n")
    git(p, "add", "dir/file")
    git(p, "commit", "-q", "-m", "tree")
    target = git(p, "rev-parse", "HEAD").stdout.strip()
    git(p, "reset", "--hard", first)
    (p / "dir").write_text("untracked obstruction\n")
    status = git(p, "status", "--porcelain=v1", "--untracked-files=all").stdout
    assert "?? dir" in status
    cp = git(p, "reset", "--hard", target, check=False)
    assert cp.returncode != 0 or (p / "dir").is_dir()


def make_conflict(td):
    p = td / "r"
    init(p)
    commit_file(p, "f", "base\n", "base")
    git(p, "switch", "-q", "-c", "left")
    commit_file(p, "f", "left\n", "left")
    git(p, "switch", "-q", "master")
    commit_file(p, "f", "right\n", "right")
    cp = git(p, "merge", "left", check=False)
    assert cp.returncode != 0
    return p


def test_conflict_stages(td):
    p = make_conflict(td)
    stages = git(p, "ls-files", "-u").stdout
    assert "\t1\tf" in stages or " 1\tf" in stages
    assert "\t2\tf" in stages or " 2\tf" in stages
    assert "\t3\tf" in stages or " 3\tf" in stages


def test_conflict_abort(td):
    p = make_conflict(td)
    before = git(p, "rev-parse", "HEAD").stdout.strip()
    git(p, "merge", "--abort")
    assert (
        git(p, "rev-parse", "HEAD").stdout.strip() == before
        and git(p, "ls-files", "-u").stdout == ""
    )


def test_tag_prune_candidates(td):
    r = td / "r.git"
    git(td, "init", "-q", "--bare", str(r))
    p = td / "p"
    init(p)
    commit_file(p, "f", "x\n", "x")
    git(p, "tag", "keep")
    git(p, "tag", "local-only")
    git(p, "remote", "add", "origin", str(r))
    git(p, "push", "-q", "origin", "refs/tags/keep")
    remote = {
        line.split("refs/tags/", 1)[1]
        for line in git(
            p, "ls-remote", "--tags", "--refs", "origin"
        ).stdout.splitlines()
    }
    local = set(git(p, "tag", "--list").stdout.splitlines())
    assert local - remote == {"local-only"}


def test_atomic_multi_ref_push(td):
    r = td / "r.git"
    git(td, "init", "-q", "--bare", str(r))
    p = td / "p"
    init(p)
    commit_file(p, "f", "x\n", "x")
    git(p, "branch", "one")
    git(p, "branch", "two")
    git(p, "remote", "add", "origin", str(r))
    git(
        p,
        "push",
        "-q",
        "--atomic",
        "origin",
        "one:refs/heads/one",
        "two:refs/heads/two",
    )
    refs = git(p, "ls-remote", "--heads", "origin").stdout
    assert "refs/heads/one" in refs and "refs/heads/two" in refs


def test_submodule_gitlink(td):
    sub = td / "sub"
    init(sub)
    oid = commit_file(sub, "s", "sub\n", "sub")
    parent = td / "parent"
    init(parent)
    commit_file(parent, "p", "parent\n", "parent")
    git(
        parent,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        "-q",
        str(sub),
        "deps/sub",
    )
    git(parent, "commit", "-q", "-am", "add submodule")
    tree = git(parent, "ls-tree", "HEAD", "deps/sub").stdout
    assert tree.startswith("160000 commit ") and oid in tree


def test_pickaxe(td):
    p = td / "r"
    init(p)
    commit_file(p, "f", "base\n", "base")
    target = commit_file(p, "f", "base\nNEEDLE\n", "needle")
    out = git(p, "log", "-SNEEDLE", "--format=%H", "--", "f").stdout.splitlines()
    assert out[0] == target


def test_bisect_oracle(td):
    p = td / "r"
    init(p)
    commits = []
    for i in range(6):
        commits.append(commit_file(p, "value", f"{i}\n", f"c{i}"))
    git(p, "bisect", "start", commits[-1], commits[0])
    while True:
        val = int((p / "value").read_text().strip())
        cp = git(p, "bisect", "bad" if val >= 3 else "good", check=False)
        text = cp.stdout + cp.stderr
        if "first bad commit" in text:
            break
    found = git(p, "rev-parse", "HEAD").stdout.strip()
    git(p, "bisect", "reset")
    assert found == commits[3]


def test_remote_names(td):
    p = td / "r"
    init(p)
    commit_file(p, "f", "x\n", "x")
    git(p, "remote", "add", "team.one/test", str(td / "none.git"))
    names = git(p, "remote").stdout.splitlines()
    assert names == ["team.one/test"]


def load_helper(rel, name):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).resolve().parents[1] / rel
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_malformed_remote_isolation(td):
    p = td / "r"
    init(p)
    commit_file(p, "f", "x\n", "x")
    git(
        p,
        "remote",
        "add",
        "good",
        "https://user:pass@example.com/repo.git?token=secret",
    )
    git(p, "remote", "add", "bad", "ssh://[broken")
    helper = load_helper(
        "skills/manage-remotes/scripts/inspect_remotes.py", "inspect_remotes_a"
    )
    data = helper.inspect(p)
    assert set(data["remotes"]) == {"good", "bad"}
    assert data["remotes"]["bad"]["url"][0]["classified"] is False


def test_fail_closed_redaction(td):
    helper = load_helper(
        "skills/manage-remotes/scripts/inspect_remotes.py", "inspect_remotes_b"
    )
    safe = helper.sanitize_url(
        "https://user:password@example.com/repo.git?token=x#frag"
    )
    opaque = helper.sanitize_url("custom-secret-format")
    assert (
        "password" not in safe["display"]
        and "token" not in safe["display"]
        and safe["classified"]
    )
    assert opaque == {"display": "", "classified": False}


def test_local_remote_identity(td):
    helper = load_helper(
        "skills/manage-remotes/scripts/inspect_remotes.py", "inspect_remotes_local"
    )
    absolute = helper.sanitize_url("/srv/git/project.git")
    file_url = helper.sanitize_url("file:///srv/git/project.git")
    windows = helper.sanitize_url(r"C:\git\project.git")
    assert absolute == {"display": "/srv/git/project.git", "classified": True}
    assert file_url == {"display": "file:///srv/git/project.git", "classified": True}
    assert windows == {"display": r"C:\git\project.git", "classified": True}


def init_build_repo(td):
    p = td / "pkg"
    p.mkdir()
    git(p, "init", "-q")
    git(p, "config", "user.name", "T")
    git(p, "config", "user.email", "t@example.invalid")
    (p / "tracked").write_text("x")
    git(p, "add", "tracked")
    git(p, "commit", "-q", "-m", "base")
    return p


def test_release_tracked_only(td):
    mod = load_helper("scripts/build_release.py", "build_release_a")
    p = init_build_repo(td)
    (p / "untracked").write_text("u")
    entries = mod.tracked_files(p)
    assert [x.rel.as_posix() for x in entries] == ["tracked"]


def test_release_symlink_rejected(td):
    mod = load_helper("scripts/build_release.py", "build_release_b")
    p = init_build_repo(td)
    os.symlink("tracked", p / "link")
    git(p, "add", "link")
    try:
        mod.tracked_files(p)
    except SystemExit as e:
        assert "symlink" in str(e)
    else:
        raise AssertionError("tracked symlink accepted")


def test_release_dirty_rejected(td):
    mod = load_helper("scripts/build_release.py", "build_release_c")
    p = init_build_repo(td)
    (p / "tracked").write_text("dirty")
    try:
        mod.require_clean_tracked_state(p)
    except SystemExit as e:
        assert "committed tracked files" in str(e)
    else:
        raise AssertionError("dirty tracked state accepted")


def test_release_deterministic(td):
    mod = load_helper("scripts/build_release.py", "build_release_d")
    p = init_build_repo(td)
    entries = mod.tracked_files(p)
    catalog = {
        "package_version": "x",
        "release_date": "2026-07-15",
        "compatibility": {},
        "skills": [],
        "base_release": {},
    }
    original = mod.source_revision
    mod.source_revision = lambda root=mod.ROOT: "0" * 40
    try:
        assert mod.archive_bytes(entries, catalog) == mod.archive_bytes(
            entries, catalog
        )
    finally:
        mod.source_revision = original


def test_installer_preflight(td):
    root = Path(__file__).resolve().parents[1]
    target = td / "skills"
    target.mkdir()
    (target / "configure-git").mkdir()
    cp = subprocess.run(
        [sys.executable, str(root / "scripts/link_skills.py"), "--target", str(target)],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 2 and not any(x.is_symlink() for x in target.iterdir())


def test_installer_dry_run(td):
    root = Path(__file__).resolve().parents[1]
    target = td / "skills"
    cp = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/link_skills.py"),
            "--target",
            str(target),
            "--dry-run",
        ],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0 and not target.exists()


def test_skipped_validation_metadata(td):
    mod = load_helper("scripts/build_release.py", "build_release_e")
    p = init_build_repo(td)
    entries = mod.tracked_files(p)
    catalog = {
        "package_version": "x",
        "release_date": "2026-07-15",
        "compatibility": {},
        "skills": [],
        "base_release": {},
    }
    original = mod.source_revision
    mod.source_revision = lambda root=mod.ROOT: "0" * 40
    try:
        rec = mod.release_record(
            entries,
            catalog,
            False,
            False,
            {"filename": "x.zip", "sha256": "0", "size_bytes": 0},
        )
    finally:
        mod.source_revision = original
    assert (
        rec["validation"]["result"] == "skipped"
        and rec["validation"]["commands_executed"] == []
        and rec["validation"]["reproducibility_check"] == "not-run"
    )


def test_installer_rollback(td):
    import pathlib

    mod = load_helper("scripts/link_skills.py", "link_skills_test")
    target = td / "skills"
    original_argv = sys.argv[:]
    original = pathlib.Path.symlink_to
    calls = {"n": 0}

    def flaky(self, target_path, target_is_directory=False):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("injected link failure")
        return original(self, target_path, target_is_directory=target_is_directory)

    pathlib.Path.symlink_to = flaky
    sys.argv = ["link_skills.py", "--target", str(target)]
    try:
        rc = mod.main()
    finally:
        pathlib.Path.symlink_to = original
        sys.argv = original_argv
    assert rc == 3 and (not target.exists() or not any(target.iterdir()))


def test_release_provenance_fields(td):
    mod = load_helper("scripts/build_release.py", "build_release_provenance")
    p = init_build_repo(td)
    entries = mod.tracked_files(p)
    catalog = {
        "package_version": "x",
        "release_date": "2026-07-15",
        "compatibility": {},
        "skills": [],
        "base_release": {
            "tag": "v1.0.0",
            "commit": "1d513f5b29332c406c33705c42ccec6dfaf86e3c",
        },
    }
    original = mod.source_revision
    mod.source_revision = lambda root=mod.ROOT: "1" * 40
    try:
        metadata = mod.release_metadata(entries, catalog)
    finally:
        mod.source_revision = original
    identity = metadata["source_identity"]
    assert identity["base_revision"] == catalog["base_release"]
    assert identity["source_revision"] == {"kind": "git-commit", "commit": "1" * 40}
    assert identity["source_tree_sha256"]


def main(argv=None):
    tests = [
        ("mailbox replay", test_mailbox),
        ("shallow deepen repair", test_shallow),
        ("corruption detection and additive restore", test_corruption_detection),
        ("stack bottom-up restack", test_stack),
        ("vendor snapshot containment", test_vendor_branch),
        ("actual git subtree update", test_actual_subtree),
        ("conditional identity origin", test_identity_include),
        ("GPG signing and reviewed hook path", test_signing_and_hook),
        ("exact branch lease rejects stale publication", test_exact_lease),
        ("exact tag lease rejects stale publication", test_tag_exact_lease),
        ("post-push remote OID verification", test_push_post_verification),
        ("annotated tag peeling", test_tag_peeling),
        ("NUL-safe worktree inventory", test_worktree_nul),
        ("destructive clean preview", test_clean_preview),
        ("non-obstructing hard reset", test_hard_reset_non_obstructing),
        ("obstructing hard reset detection", test_hard_reset_obstruction_detected),
        ("conflict index stages", test_conflict_stages),
        ("conflict abort", test_conflict_abort),
        ("shared tag prune candidates", test_tag_prune_candidates),
        ("atomic multi-ref push", test_atomic_multi_ref_push),
        ("submodule gitlink", test_submodule_gitlink),
        ("history pickaxe", test_pickaxe),
        ("bisect oracle", test_bisect_oracle),
        ("remote names with dots/slashes", test_remote_names),
        ("malformed remote isolation", test_malformed_remote_isolation),
        ("fail-closed remote redaction", test_fail_closed_redaction),
        ("local remote identity", test_local_remote_identity),
        ("tracked-only release inputs", test_release_tracked_only),
        ("tracked symlink rejection", test_release_symlink_rejected),
        ("dirty release state rejection", test_release_dirty_rejected),
        ("deterministic archive bytes", test_release_deterministic),
        ("skipped validation sidecar metadata", test_skipped_validation_metadata),
        ("release provenance fields", test_release_provenance_fields),
        ("installer all-target preflight", test_installer_preflight),
        ("installer rollback", test_installer_rollback),
        ("installer dry-run no mutation", test_installer_dry_run),
        ("reflog additive recovery", test_reflog),
        ("pathological filename safety", test_pathological_filename),
    ]
    parser = argparse.ArgumentParser(
        description="Run disposable Git and package semantic tests."
    )
    parser.add_argument(
        "--list", action="store_true", help="List test names without running them."
    )
    args = parser.parse_args(argv)
    if args.list:
        for name, _ in tests:
            print(name)
        return 0
    runner = TestRunner()
    for name, fn in tests:
        with tempfile.TemporaryDirectory(prefix="git-skills-") as d:
            runner.run(name, lambda fn=fn, d=d: fn(Path(d)))
    print(f"PASS smoke_test_git: {runner.ok} passed, " f"{runner.skip} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
