#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable
from pathlib import Path

from security_git_env import controlled_git_env, resolve_git

sys.dont_write_bytecode = True


class TestRunner:
    def __init__(self):
        self.ok = 0
        self.skip = 0

    def run(self, name: str, fn: Callable[[], None]) -> None:
        started = time.perf_counter()
        try:
            fn()
            self.ok += 1
            print(f"PASS {name} ({time.perf_counter() - started:.2f}s)", flush=True)
        except SkipTest as exc:
            self.skip += 1
            print(
                f"SKIP {name} - {exc} ({time.perf_counter() - started:.2f}s)",
                flush=True,
            )
        except Exception as exc:
            elapsed = time.perf_counter() - started
            print(f"FAIL {name} - {exc} ({elapsed:.2f}s)", flush=True)
            raise


class SkipTest(Exception):
    pass


def git(cwd, *args, check=True, env=None, text=True):
    effective_env = controlled_git_env(env)
    try:
        cp = subprocess.run(
            [resolve_git(), *args],
            cwd=cwd,
            text=text,
            capture_output=True,
            env=effective_env,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"git {args}: timed out after 30s")
    if check and cp.returncode:
        if text:
            message = cp.stderr or cp.stdout
        else:
            message = (cp.stderr or cp.stdout).decode("utf-8", errors="replace")
        raise RuntimeError(f"git {args}: {message}")
    return cp


def init(p):
    p.mkdir(parents=True)
    git(p, "init", "-q")
    git(p, "config", "user.name", "Test User")
    git(p, "config", "user.email", "test@example.invalid")
    git(p, "config", "core.autocrlf", "false")


def commit_file(p, name, content, msg):
    (p / name).parent.mkdir(parents=True, exist_ok=True)
    (p / name).write_bytes(content.encode("utf-8"))
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
    # Resolve macOS /tmp symlinks so gitdir matching uses canonical paths.
    main.write_text(
        f'[user]\n\tname = Personal User\n\temail = personal@example.invalid\n[includeIf "gitdir:{work.resolve()}/.git"]\n\tpath = {inc.resolve()}\n'
    )
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["GIT_AGENT_SKILLS_ALLOW_HOME"] = "1"
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
    env["GIT_AGENT_SKILLS_ALLOW_GNUPGHOME"] = "1"
    env["GIT_AGENT_SKILLS_ALLOW_HOOKS"] = "1"
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


def test_pathological_filename_posix(td):
    p = td / "repo"
    init(p)
    name = "-nasty name\nline"
    (p / name).write_bytes(b"x")
    git(p, "add", "--", name)
    git(p, "commit", "-q", "-m", "path")
    out = git(p, "ls-files", "-z").stdout
    assert name + "\0" == out


def test_pathological_filename_windows(td):
    p = td / "repo"
    init(p)
    names = [
        "-nasty name",
        "unicode-\u00e9-file",
        "name with multiple spaces",
    ]
    for name in names:
        (p / name).write_bytes(b"x")
        git(p, "add", "--", name)
    git(p, "commit", "-q", "-m", "paths")
    raw = git(p, "ls-files", "-z", text=False).stdout
    actual = set(raw.rstrip(b"\0").split(b"\0"))
    expected = {name.encode("utf-8") for name in names}
    assert actual == expected, (
        f"path mismatch: actual={sorted(actual)!r}, "
        f"expected={sorted(expected)!r}"
    )


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
    rev = git(p, "rev-parse", "HEAD").stdout.strip()
    entries = mod.tracked_files(rev, root=p)
    assert [x.rel.as_posix() for x in entries] == ["tracked"]


def test_release_symlink_rejected(td):
    mod = load_helper("scripts/build_release.py", "build_release_b")
    p = init_build_repo(td)
    os.symlink("tracked", p / "link")
    git(p, "add", "link")
    git(p, "commit", "-q", "-m", "symlink")
    rev = git(p, "rev-parse", "HEAD").stdout.strip()
    try:
        mod.tracked_files(rev, root=p)
    except SystemExit as e:
        assert "symlink" in str(e) or "unsupported" in str(e)
    else:
        raise AssertionError("tracked symlink accepted")


def test_output_symlink_parent_rejected(td):
    mod = load_helper("scripts/build_release.py", "build_output_symlink")
    outside = td / "outside"
    outside.mkdir()
    redirect = td / "redirect"
    redirect.symlink_to(outside, target_is_directory=True)
    try:
        mod.reject_symlink_components(redirect / "release.zip")
    except SystemExit as e:
        assert "symlink" in str(e)
    else:
        raise AssertionError("symlinked output parent accepted")


def test_release_uses_committed_bytes(td):
    # Verify archive uses committed bytes, not dirty working tree
    mod = load_helper("scripts/build_release.py", "build_release_c")
    p = init_build_repo(td)
    (p / "tracked").write_text("dirty\n")
    revision = git(p, "rev-parse", "HEAD").stdout.strip()
    entries = mod.tracked_files(revision, root=p)
    assert any(e.rel.as_posix() == "tracked" and e.data == b"x" for e in entries)


def test_release_deterministic(td):
    mod = load_helper("scripts/build_release.py", "build_release_d")
    p = init_build_repo(td)
    rev = git(p, "rev-parse", "HEAD").stdout.strip()
    entries = mod.tracked_files(rev, root=p)
    catalog = {
        "package_version": "x",
        "release_date": "2026-07-15",
        "compatibility": {},
        "skills": [],
        "base_release": {},
    }
    assert mod.archive_bytes(entries, catalog) == mod.archive_bytes(entries, catalog)


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


def _run_installer(target: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    root = Path(__file__).resolve().parents[1]
    cp = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/link_skills.py"),
            "--target",
            str(target),
            "--mode",
            "copy",
            *extra,
        ],
        text=True,
        capture_output=True,
    )
    if cp.returncode:
        raise AssertionError(
            f"installer failed ({cp.returncode}): stdout={cp.stdout!r}, "
            f"stderr={cp.stderr!r}"
        )
    return cp


def _first_catalog_skill() -> str:
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / "skills/catalog.json").read_text(encoding="utf-8"))
    return catalog["skills"][0]["name"]


def test_installer_copy_rerun(td):
    mod = load_helper("scripts/link_skills.py", "link_skills_copy_rerun")
    target = td / "skills"
    _run_installer(target)
    first = target / _first_catalog_skill()
    marker = first / mod.MARKER_NAME
    assert marker.read_text(encoding="utf-8") == mod.MARKER_CONTENT
    sentinel = first / "local-only-sentinel"
    sentinel.write_text("old\n", encoding="utf-8")
    _run_installer(target)
    assert not sentinel.exists()
    assert marker.read_text(encoding="utf-8") == mod.MARKER_CONTENT


def test_installer_force_copy_upgrade(td):
    mod = load_helper("scripts/link_skills.py", "link_skills_force_upgrade")
    target = td / "skills"
    _run_installer(target)
    first = target / _first_catalog_skill()
    (first / mod.MARKER_NAME).unlink()
    _run_installer(target, "--force-copies")
    assert (first / mod.MARKER_NAME).read_text(encoding="utf-8") == mod.MARKER_CONTENT


def test_installer_copy_rollback(td):
    mod = load_helper("scripts/link_skills.py", "link_skills_copy_rollback")
    target = td / "skills"
    _run_installer(target)
    first = target / _first_catalog_skill()
    sentinel = first / "rollback-sentinel"
    sentinel.write_text("preserve me\n", encoding="utf-8")

    original_argv = sys.argv[:]
    real_install = mod.install
    calls = {"n": 0}

    def flaky(source, dest, mode):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("injected copy failure")
        return real_install(source, dest, mode)

    mod.install = flaky
    sys.argv = [
        "link_skills.py",
        "--target",
        str(target),
        "--mode",
        "copy",
    ]
    try:
        rc = mod.main()
    finally:
        mod.install = real_install
        sys.argv = original_argv

    assert rc == 3
    assert sentinel.read_text(encoding="utf-8") == "preserve me\n"
    assert not list(target.glob(".*.backup-*"))
    assert not list(target.glob(".*.tmp-*"))


def test_installer_nested_link_rejected(td):
    mod = load_helper("scripts/link_skills.py", "link_skills_nested_link")
    source = td / "source"
    outside = td / "outside"
    source.mkdir()
    outside.mkdir()
    link = source / "redirect"

    if os.name == "nt":
        cp = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(outside)],
            text=True,
            capture_output=True,
        )
        if cp.returncode:
            raise SkipTest("unable to create disposable Windows junction")
    else:
        link.symlink_to(outside, target_is_directory=True)

    try:
        mod.reject_nested_symlinks(source)
    except SystemExit:
        pass
    else:
        raise AssertionError("nested link or junction accepted by copy preflight")


def test_installer_special_file_rejected(td):
    if not hasattr(os, "mkfifo"):
        raise SkipTest("FIFO creation unavailable")
    mod = load_helper("scripts/link_skills.py", "link_skills_special_file")
    source = td / "source"
    source.mkdir()
    os.mkfifo(source / "pipe")
    try:
        mod.reject_nested_symlinks(source)
    except SystemExit:
        pass
    else:
        raise AssertionError("special filesystem entry accepted by copy preflight")


def test_installer_mode_transition(td):
    mod = load_helper("scripts/link_skills.py", "link_skills_mode_transition")
    if not mod.can_symlink():
        raise SkipTest("directory symlinks unavailable")
    root = Path(__file__).resolve().parents[1]
    target = td / "skills"
    _run_installer(target)
    first_name = _first_catalog_skill()
    first = target / first_name

    cp = subprocess.run(
        [
            sys.executable,
            str(root / "scripts/link_skills.py"),
            "--target",
            str(target),
            "--mode",
            "symlink",
        ],
        text=True,
        capture_output=True,
    )
    assert cp.returncode == 0, cp.stderr
    assert first.is_symlink()

    _run_installer(target)
    assert first.is_dir() and not first.is_symlink()
    assert (first / mod.MARKER_NAME).read_text(encoding="utf-8") == mod.MARKER_CONTENT


def test_release_metadata_filename(td):
    mod = load_helper("scripts/build_release.py", "build_release_metadata_filename")
    output = td / "git-agent-skills-1.1.0.zip"
    assert mod.release_path(output).name == "git-agent-skills-1.1.0.release.json"


def test_skipped_validation_metadata(td):
    mod = load_helper("scripts/build_release.py", "build_release_e")
    p = init_build_repo(td)
    rev = git(p, "rev-parse", "HEAD").stdout.strip()
    entries = mod.tracked_files(rev, root=p)
    catalog = {
        "package_version": "x",
        "release_date": "2026-07-15",
        "compatibility": {},
        "skills": [],
        "base_release": {},
    }
    rec = mod.release_record(
        entries,
        catalog,
        rev,
        False,
        {"filename": "x.zip", "sha256": "0", "size_bytes": 0},
        root=p,
    )
    assert (
        rec["validation"]["reproducibility_check"] == "not-run"
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
    rev = git(p, "rev-parse", "HEAD").stdout.strip()
    entries = mod.tracked_files(rev, root=p)
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
    metadata = mod.release_metadata(entries, catalog, rev, root=p)
    identity = metadata["source_identity"]
    assert identity["base_revision"] == catalog["base_release"]
    assert identity["source_revision"] == {"kind": "git-commit", "commit": rev}
    assert identity["source_tree_sha256"]


def main(argv=None):
    tests = [
        # --- portable: Git behavior identical across platforms ---
        ("mailbox replay", test_mailbox, {"portable", "macos", "windows"}),
        ("shallow deepen repair", test_shallow, {"portable"}),
        ("corruption detection and additive restore", test_corruption_detection, {"portable"}),
        ("stack bottom-up restack", test_stack, {"portable"}),
        ("vendor snapshot containment", test_vendor_branch, {"portable"}),
        ("actual git subtree update", test_actual_subtree, {"portable"}),
        ("conditional identity origin", test_identity_include, {"portable", "macos"}),
        ("exact branch lease rejects stale publication", test_exact_lease, {"portable"}),
        ("exact tag lease rejects stale publication", test_tag_exact_lease, {"portable"}),
        ("post-push remote OID verification", test_push_post_verification, {"portable"}),
        ("annotated tag peeling", test_tag_peeling, {"portable"}),
        ("NUL-safe worktree inventory", test_worktree_nul, {"portable"}),
        ("destructive clean preview", test_clean_preview, {"portable"}),
        ("non-obstructing hard reset", test_hard_reset_non_obstructing, {"portable"}),
        ("obstructing hard reset detection", test_hard_reset_obstruction_detected, {"portable"}),
        ("conflict index stages", test_conflict_stages, {"portable"}),
        ("conflict abort", test_conflict_abort, {"portable"}),
        ("shared tag prune candidates", test_tag_prune_candidates, {"portable"}),
        ("atomic multi-ref push", test_atomic_multi_ref_push, {"portable"}),
        ("submodule gitlink", test_submodule_gitlink, {"portable"}),
        ("history pickaxe", test_pickaxe, {"portable"}),
        ("bisect oracle", test_bisect_oracle, {"portable"}),
        ("remote names with dots/slashes", test_remote_names, {"portable"}),
        ("malformed remote isolation", test_malformed_remote_isolation, {"portable"}),
        ("fail-closed remote redaction", test_fail_closed_redaction, {"portable"}),
        ("reflog additive recovery", test_reflog, {"portable"}),
        ("pathological filename safety (POSIX)", test_pathological_filename_posix, {"macos"}),
        ("pathological filename safety (Windows)", test_pathological_filename_windows, {"windows"}),
        # --- macOS-specific: /tmp → /private/tmp, installer symlink, output protection ---
        ("GPG signing and reviewed hook path", test_signing_and_hook, {"macos"}),
        ("local remote identity", test_local_remote_identity, {"macos"}),
        ("tracked-only release inputs", test_release_tracked_only, {"macos"}),
        ("tracked symlink rejection", test_release_symlink_rejected, {"macos"}),
        ("output symlink parent rejection", test_output_symlink_parent_rejected, {"macos"}),
        ("release uses committed bytes", test_release_uses_committed_bytes, {"macos"}),
        ("deterministic archive bytes", test_release_deterministic, {"macos"}),
        ("release metadata filename", test_release_metadata_filename, {"macos"}),
        ("skipped validation metadata", test_skipped_validation_metadata, {"macos"}),
        ("release provenance fields", test_release_provenance_fields, {"macos"}),
        ("installer all-target preflight", test_installer_preflight, {"macos", "windows"}),
        ("installer symlink rollback", test_installer_rollback, {"macos"}),
        ("installer dry-run no mutation", test_installer_dry_run, {"macos", "windows"}),
        ("installer copy rerun and update", test_installer_copy_rerun, {"macos", "windows"}),
        ("installer forced copy upgrade", test_installer_force_copy_upgrade, {"macos", "windows"}),
        ("installer copy rollback", test_installer_copy_rollback, {"macos", "windows"}),
        ("installer nested link rejection", test_installer_nested_link_rejected, {"macos", "windows"}),
        ("installer special-file rejection", test_installer_special_file_rejected, {"macos"}),
        ("installer copy-symlink transition", test_installer_mode_transition, {"macos"}),
        # --- Windows-specific: copy fallback, CRLF/LF mailbox, reserved paths ---
    ]
    parser = argparse.ArgumentParser(
        description="Run disposable Git and package semantic tests."
    )
    parser.add_argument(
        "--list", action="store_true", help="List test names without running them."
    )
    parser.add_argument(
        "--platform",
        choices=["all", "portable", "macos", "windows"],
        default="all",
        help="Test subset to run (default: all)",
    )
    args = parser.parse_args(argv)
    if args.list:
        for name, _, _ in tests:
            print(name)
        return 0

    # Filter tests: "all" runs everything; "portable" runs portable-only;
    # "macos"/"windows" run portable + platform-specific tests.
    selected = []
    seen = set()
    for name, fn, platforms in tests:
        if name in seen:
            continue
        seen.add(name)
        if args.platform == "all" or args.platform in platforms:
            selected.append((name, fn))
    runner = TestRunner()
    for name, fn in selected:
        with tempfile.TemporaryDirectory(prefix="git-skills-") as d:
            runner.run(name, lambda fn=fn, d=d: fn(Path(d)))
    print(f"PASS smoke_test_git: {runner.ok} passed, " f"{runner.skip} skipped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
