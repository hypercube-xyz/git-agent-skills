#!/usr/bin/env python3
"""Small Git behavior checks for inspection and branch-policy guidance."""
from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
from pathlib import Path


def git(repo: Path, *args: str, env_extra: dict[str, str] | None = None, check: bool = True) -> str:
    env = ENV.copy()
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        ["git", *args], cwd=repo, env=env, capture_output=True, text=True, timeout=30
    )
    if check and result.returncode:
        raise AssertionError(f"git {args!r} failed: {result.stderr.strip()}")
    return (result.stdout if result.returncode == 0 else result.stderr).strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stale_stat(path: Path) -> None:
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns - 60_000_000_000))


def init(repo: Path) -> None:
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    git(repo, "config", "core.autocrlf", "false")


def commit_file(repo: Path, name: str, content: str) -> str:
    (repo / name).write_text(content, encoding="utf-8")
    git(repo, "add", "--", name)
    git(repo, "commit", "-qm", name)
    return git(repo, "rev-parse", "HEAD")


def test_optional_index_refresh(root: Path) -> None:
    repo = root / "index-refresh"
    init(repo)
    tracked = repo / "unchanged.txt"
    commit_file(repo, "unchanged.txt", "same content\n")
    index = repo / ".git" / "index"

    # An unchanged file with stale stat data needs an index refresh. Inspection
    # with no optional locks must report clean without writing that refresh.
    stale_stat(tracked)
    before = digest(index)
    assert git(repo, "--no-optional-locks", "-c", "core.fsmonitor=false", "status", "--porcelain") == ""
    assert digest(index) == before, "read-only status rewrote the index"

    # Negative control: ordinary status refreshes the cached stat entry.
    assert git(repo, "-c", "core.fsmonitor=false", "status", "--porcelain") == ""
    assert digest(index) != before, "fixture did not trigger an ordinary index refresh"


def test_branch_copy_policy(root: Path) -> None:
    repo = root / "branch-copy"
    init(repo)
    commit_file(repo, "file.txt", "content\n")
    source = git(repo, "branch", "--show-current")
    git(repo, "config", f"branch.{source}.pushRemote", "production")
    git(repo, "config", f"branch.{source}.rebase", "true")
    git(repo, "branch", "-c", source, "copied")
    assert git(repo, "config", "--get", "branch.copied.pushRemote") == "production"
    assert git(repo, "config", "--get", "branch.copied.rebase") == "true"
    assert git(repo, "rev-parse", source) == git(repo, "rev-parse", "copied")


def notes_rewrite_case(root: Path, command: str, prevent_rewrite: bool) -> None:
    repo = root / f"notes-{command}-{'safe' if prevent_rewrite else 'unsafe'}"
    init(repo)
    commit_file(repo, "base.txt", "base\n")
    main = git(repo, "branch", "--show-current")
    git(repo, "config", "notes.rewriteRef", "refs/notes/commits")
    git(repo, "config", f"notes.rewrite.{command}", "true")
    rewrite_env = {"GIT_NOTES_REWRITE_REF": "refs/notes/commits"}

    if command == "amend":
        old = git(repo, "rev-parse", "HEAD")
    else:
        git(repo, "switch", "-q", "-c", "feature")
        old = commit_file(repo, "feature.txt", "feature\n")
        git(repo, "switch", "-q", main)
        commit_file(repo, "upstream.txt", "upstream\n")
        git(repo, "switch", "-q", "feature")

    git(repo, "notes", "add", "-m", "retain this note", old)
    note_ref_before = git(repo, "rev-parse", "refs/notes/commits")
    scoped = ["-c", f"notes.rewrite.{command}=false"] if prevent_rewrite else []
    if command == "amend":
        git(repo, *scoped, "commit", "--amend", "-qm", "amended", env_extra=rewrite_env)
    else:
        git(repo, *scoped, "rebase", "-q", main, env_extra=rewrite_env)
    new = git(repo, "rev-parse", "HEAD")
    assert new != old, f"{command} did not rewrite its commit"
    note_ref_after = git(repo, "rev-parse", "refs/notes/commits")
    note_on_new = git(repo, "notes", "show", new, check=False)
    if prevent_rewrite:
        assert note_ref_after == note_ref_before, f"scoped {command} changed notes ref"
        assert "retain this note" not in note_on_new, f"scoped {command} copied note"
    else:
        assert note_ref_after != note_ref_before, f"unsafe {command} did not change notes ref"
        assert "retain this note" in note_on_new, f"unsafe {command} did not copy note"


def autostash_case(root: Path, prevent_autostash: bool) -> None:
    repo = root / f"autostash-{'safe' if prevent_autostash else 'unsafe'}"
    init(repo)
    commit_file(repo, "local.txt", "base\n")
    main = git(repo, "branch", "--show-current")
    git(repo, "switch", "-q", "-c", "feature")
    commit_file(repo, "feature.txt", "feature\n")
    git(repo, "switch", "-q", main)
    commit_file(repo, "upstream.txt", "upstream\n")
    git(repo, "switch", "-q", "feature")
    git(repo, "config", "rebase.autoStash", "true")
    git(repo, "notes", "add", "-m", "existing note", "HEAD")
    notes_before = git(repo, "rev-parse", "refs/notes/commits")
    (repo / "local.txt").write_bytes(b"local uncommitted bytes\n")
    head_before = git(repo, "rev-parse", "HEAD")
    index_before = digest(repo / ".git" / "index")
    bytes_before = (repo / "local.txt").read_bytes()

    scoped = ["-c", "rebase.autoStash=false"] if prevent_autostash else []
    result = subprocess.run(
        ["git", *scoped, "rebase", "-q", main],
        cwd=repo,
        env=ENV,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if prevent_autostash:
        assert result.returncode != 0, "scoped rebase unexpectedly proceeded with dirty work"
        assert git(repo, "rev-parse", "HEAD") == head_before
        assert digest(repo / ".git" / "index") == index_before
        assert (repo / "local.txt").read_bytes() == bytes_before
        assert git(repo, "rev-parse", "refs/notes/commits") == notes_before
    else:
        assert result.returncode == 0, f"inherited autostash rebase failed: {result.stderr}"
        assert git(repo, "rev-parse", "HEAD") != head_before
        assert (repo / "local.txt").read_bytes() == bytes_before


def merge_autostash_case(root: Path, prevent_autostash: bool) -> None:
    repo = root / f"merge-autostash-{'safe' if prevent_autostash else 'unsafe'}"
    init(repo)
    commit_file(repo, "local.txt", "base\n")
    main = git(repo, "branch", "--show-current")
    git(repo, "switch", "-q", "-c", "feature")
    commit_file(repo, "feature.txt", "feature\n")
    git(repo, "switch", "-q", main)
    commit_file(repo, "upstream.txt", "upstream\n")
    git(repo, "switch", "-q", "feature")
    git(repo, "config", "merge.autoStash", "true")
    (repo / "local.txt").write_bytes(b"local uncommitted bytes\n")
    bytes_before = (repo / "local.txt").read_bytes()
    head_before = git(repo, "rev-parse", "HEAD")

    scoped = ["-c", "merge.autoStash=false"] if prevent_autostash else []
    result = subprocess.run(
        ["git", *scoped, "merge", "--no-edit", main],
        cwd=repo,
        env=ENV,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, f"nonconflicting merge failed: {result.stderr}"
    output = result.stdout + result.stderr
    assert ("autostash:" in output.lower()) != prevent_autostash, output
    assert git(repo, "rev-parse", "HEAD") != head_before
    assert (repo / "local.txt").read_bytes() == bytes_before
    assert (repo / "feature.txt").read_text(encoding="utf-8") == "feature\n"
    assert (repo / "upstream.txt").read_text(encoding="utf-8") == "upstream\n"


def ref_correction_case(root: Path, checked_out: bool) -> None:
    repo = root / f"ref-correction-{'unsafe' if checked_out else 'safe'}"
    init(repo)
    old = commit_file(repo, "tracked.txt", "old\n")
    new = commit_file(repo, "tracked.txt", "new\n")
    branch = git(repo, "branch", "--show-current")
    head_before = git(repo, "rev-parse", "HEAD")
    index_before = digest(repo / ".git" / "index")
    bytes_before = (repo / "tracked.txt").read_bytes()

    if checked_out:
        git(repo, "update-ref", f"refs/heads/{branch}", old, new)
        assert git(repo, "rev-parse", "HEAD") == old
        assert digest(repo / ".git" / "index") == index_before
        assert (repo / "tracked.txt").read_bytes() == bytes_before
        assert "tracked.txt" in git(repo, "--no-optional-locks", "diff", "--cached", "--name-only")
    else:
        # Correct only an inactive quarantine ref. The checked-out branch and
        # its index/files stay consistent throughout the exact ref update.
        git(repo, "update-ref", "refs/recovery/candidate", old)
        git(repo, "update-ref", "refs/recovery/candidate", new, old)
        assert git(repo, "rev-parse", "refs/recovery/candidate") == new
        assert git(repo, "rev-parse", "HEAD") == head_before
        assert digest(repo / ".git" / "index") == index_before
        assert (repo / "tracked.txt").read_bytes() == bytes_before
        assert git(repo, "--no-optional-locks", "diff", "--cached", "--name-only") == ""


def test_recovery_ref_symbolic_alias(root: Path) -> None:
    repo = root / "recovery-symbolic-alias"
    init(repo)
    candidate = commit_file(repo, "candidate.txt", "candidate\n")
    head_before = git(repo, "rev-parse", "HEAD")
    zero = "0" * len(candidate)
    alias = "refs/recovery/foo"
    target = "refs/heads/unrelated"
    git(repo, "symbolic-ref", alias, target)
    assert git(repo, "symbolic-ref", "-q", alias) == target
    assert git(repo, "for-each-ref", "--format=%(refname)", target) == ""

    # The ordinary expected-absent update follows a dangling symbolic ref.
    git(repo, "update-ref", alias, candidate, zero)
    assert git(repo, "rev-parse", target) == candidate
    assert git(repo, "symbolic-ref", "-q", alias) == target

    # The kind check rejects the occupied alias before any safe update.
    git(repo, "update-ref", "--no-deref", target, zero, candidate)
    assert git(repo, "symbolic-ref", "-q", alias) == target
    assert git(repo, "for-each-ref", "--format=%(refname)", target) == ""
    safe = "refs/recovery/verified-absent"
    git(repo, "update-ref", "--no-deref", safe, candidate, zero)
    assert git(repo, "rev-parse", safe) == candidate

    # Git versions differ: no-deref may reject the dangling alias or replace
    # that alias with a direct ref. Neither outcome may create its target.
    probe = "refs/recovery/no-deref-probe"
    probe_target = "refs/heads/probe-target"
    git(repo, "symbolic-ref", probe, probe_target)
    result = subprocess.run(
        ["git", "update-ref", "--no-deref", probe, candidate, zero],
        cwd=repo, env=ENV, capture_output=True, text=True, timeout=30,
    )
    assert git(repo, "for-each-ref", "--format=%(refname)", probe_target) == ""
    if result.returncode == 0:
        assert git(repo, "for-each-ref", "--format=%(symref)", probe) == ""
        assert git(repo, "rev-parse", probe) == candidate
    else:
        assert git(repo, "symbolic-ref", "-q", probe) == probe_target
    assert git(repo, "symbolic-ref", "-q", alias) == target
    assert git(repo, "for-each-ref", "--format=%(refname)", target) == ""
    assert git(repo, "rev-parse", "HEAD") == head_before


def test_cutover_symbolic_alias(root: Path) -> None:
    repo = root / "cutover-symbolic-alias"
    init(repo)
    old = commit_file(repo, "old.txt", "old\n")
    new = commit_file(repo, "new.txt", "new\n")
    head_before = git(repo, "rev-parse", "HEAD")
    victim = "refs/heads/victim"
    alias = "refs/heads/branchalias"
    zero = "0" * len(old)
    git(repo, "update-ref", "--no-deref", victim, old, zero)
    git(repo, "symbolic-ref", alias, victim)
    assert git(repo, "symbolic-ref", "-q", alias) == victim

    # An OID compare-and-swap alone still updates the alias's target.
    git(repo, "update-ref", alias, new, old)
    assert git(repo, "rev-parse", victim) == new
    assert git(repo, "symbolic-ref", "-q", alias) == victim

    git(repo, "update-ref", "--no-deref", victim, old, new)
    # A symbolic name must be rejected by the kind check. --no-deref alone
    # would replace that name with a direct ref when its resolved OID matches.
    assert git(repo, "symbolic-ref", "-q", alias) == victim
    assert git(repo, "rev-parse", victim) == old
    assert git(repo, "symbolic-ref", "-q", alias) == victim
    probe = "refs/heads/alias-no-deref-probe"
    git(repo, "symbolic-ref", probe, victim)
    git(repo, "update-ref", "--no-deref", probe, new, old)
    assert git(repo, "for-each-ref", "--format=%(symref)", probe) == ""
    assert git(repo, "rev-parse", probe) == new
    assert git(repo, "rev-parse", victim) == old
    git(repo, "update-ref", "--no-deref", victim, new, old)
    assert git(repo, "rev-parse", victim) == new
    assert git(repo, "rev-parse", "HEAD") == head_before


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="git-skills-recheck-") as temp:
        root = Path(temp)
        ENV = {
            key: value
            for key, value in os.environ.items()
            if key in {"PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TMP", "TEMP", "TMPDIR"}
        }
        ENV.update(
            {
                "HOME": str(root / "home"),
                "XDG_CONFIG_HOME": str(root / "xdg"),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_TEMPLATE_DIR": str(root / "empty-template"),
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_PAGER": "cat",
            }
        )
        (root / "home").mkdir()
        (root / "xdg").mkdir()
        (root / "empty-template").mkdir()
        test_optional_index_refresh(root)
        print("PASS optional index refresh boundary")
        test_branch_copy_policy(root)
        print("PASS branch copy preserves policy")
        for command in ("amend", "rebase"):
            notes_rewrite_case(root, command, prevent_rewrite=False)
            notes_rewrite_case(root, command, prevent_rewrite=True)
            print(f"PASS {command} notes rewrite boundary")
        autostash_case(root, prevent_autostash=False)
        autostash_case(root, prevent_autostash=True)
        print("PASS rebase autostash boundary")
        merge_autostash_case(root, prevent_autostash=False)
        merge_autostash_case(root, prevent_autostash=True)
        print("PASS merge autostash boundary")
        ref_correction_case(root, checked_out=True)
        ref_correction_case(root, checked_out=False)
        print("PASS checked-out ref correction boundary")
        test_recovery_ref_symbolic_alias(root)
        print("PASS dangling symbolic recovery ref boundary")
        test_cutover_symbolic_alias(root)
        print("PASS symbolic cutover ref boundary")
