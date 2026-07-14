#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestFailure(RuntimeError):
    pass


def run(cwd: Path, *args: str, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        list(args),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={**os.environ, **(env or {})},
    )
    if check and proc.returncode:
        raise TestFailure(
            f"command failed ({proc.returncode}) in {cwd}: {' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    return proc


def git(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(cwd, "git", *args, check=check)


def init_repo(path: Path, *, bare: bool = False) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    if bare:
        git(path, "init", "--bare", "--initial-branch=main")
    else:
        git(path, "init", "--initial-branch=main")
        git(path, "config", "user.name", "Smoke Test")
        git(path, "config", "user.email", "smoke@example.invalid")
    return path


def commit_file(repo: Path, name: str, content: str, message: str) -> str:
    p = repo / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    git(repo, "add", "--", name)
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD").stdout.strip()


def status(repo: Path) -> str:
    return git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout


def test_unborn_and_porcelain(tmp: Path) -> None:
    repo = init_repo(tmp / "unborn")
    out = git(repo, "status", "--porcelain=v2", "--branch").stdout
    assert "# branch.oid (initial)" in out
    assert "# branch.head main" in out


def test_config_origin(tmp: Path) -> None:
    repo = init_repo(tmp / "config")
    git(repo, "config", "--local", "pull.rebase", "true")
    out = git(repo, "config", "--show-origin", "--show-scope", "--get-all", "pull.rebase").stdout
    assert "local" in out and "true" in out


def test_remote_redaction(tmp: Path) -> None:
    repo = init_repo(tmp / "remote")
    git(repo, "remote", "add", "origin", "https://user:supersecret@example.com/org/repo.git?token=abc")
    git(repo, "remote", "set-url", "--add", "--push", "origin", "custom::token@example.com/private")
    helper = ROOT / "skills" / "manage-remotes" / "scripts" / "inspect_remotes.py"
    out = run(repo, "python3", str(helper)).stdout
    assert "supersecret" not in out and "token@example" not in out and "token=abc" not in out
    data = json.loads(out)
    values = [x["value"] for x in data]
    assert any("example.com/org/repo.git" in v for v in values)
    assert any("<redacted-opaque-address>" in v for v in values)


def test_atomic_commit_protects_unselected(tmp: Path) -> None:
    repo = init_repo(tmp / "atomic")
    commit_file(repo, "a.txt", "base\n", "chore: base")
    (repo / "a.txt").write_text("base\nselected\n")
    (repo / "unrelated.txt").write_text("keep local\n")
    git(repo, "add", "--", "a.txt")
    staged = git(repo, "diff", "--cached", "--name-only").stdout.splitlines()
    assert staged == ["a.txt"]
    git(repo, "commit", "-m", "feat: add selected change")
    assert (repo / "unrelated.txt").read_text() == "keep local\n"
    assert "?? unrelated.txt" in status(repo)


def test_branch_delete_proof(tmp: Path) -> None:
    repo = init_repo(tmp / "branch")
    commit_file(repo, "base", "1\n", "base")
    git(repo, "switch", "-c", "feature")
    feature = commit_file(repo, "f", "x\n", "feature")
    git(repo, "switch", "main")
    assert git(repo, "merge-base", "--is-ancestor", feature, "main", check=False).returncode != 0
    assert git(repo, "branch", "-d", "feature", check=False).returncode != 0
    git(repo, "merge", "--ff-only", "feature")
    assert git(repo, "merge-base", "--is-ancestor", feature, "main").returncode == 0
    git(repo, "branch", "-d", "feature")


def test_sync_fast_forward_and_divergence(tmp: Path) -> None:
    remote = init_repo(tmp / "sync-remote.git", bare=True)
    seed = init_repo(tmp / "sync-seed")
    commit_file(seed, "f", "base\n", "base")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "main")
    a = tmp / "sync-a"
    b = tmp / "sync-b"
    git(tmp, "clone", str(remote), str(a))
    git(tmp, "clone", str(remote), str(b))
    for repo in (a, b):
        git(repo, "config", "user.name", "Smoke")
        git(repo, "config", "user.email", "smoke@example.invalid")
    commit_file(a, "a", "a\n", "a")
    git(a, "push", "origin", "main")
    git(b, "fetch", "origin")
    counts = git(b, "rev-list", "--left-right", "--count", "main...origin/main").stdout.strip()
    assert counts == "0\t1"
    git(b, "merge", "--ff-only", "origin/main")
    commit_file(a, "a2", "a2\n", "a2")
    commit_file(b, "b", "b\n", "b")
    git(a, "push", "origin", "main")
    git(b, "fetch", "origin")
    left, right = map(int, git(b, "rev-list", "--left-right", "--count", "main...origin/main").stdout.split())
    assert left == 1 and right == 1


def test_merge_fast_forward(tmp: Path) -> None:
    repo = init_repo(tmp / "merge")
    commit_file(repo, "f", "0\n", "base")
    git(repo, "switch", "-c", "topic")
    tip = commit_file(repo, "f", "0\n1\n", "topic")
    git(repo, "switch", "main")
    before_count = int(git(repo, "rev-list", "--count", "HEAD").stdout)
    git(repo, "merge", "--ff-only", "topic")
    assert git(repo, "rev-parse", "HEAD").stdout.strip() == tip
    assert int(git(repo, "rev-list", "--count", "HEAD").stdout) == before_count + 1


def test_preservation_patch_does_not_clean(tmp: Path) -> None:
    repo = init_repo(tmp / "preserve")
    commit_file(repo, "f", "base\n", "base")
    (repo / "f").write_text("base\nchange\n")
    (repo / "u").write_text("untracked\n")
    patch = tmp / "work.patch"
    proc = run(repo, "git", "diff", check=True)
    patch.write_text(proc.stdout)
    assert patch.stat().st_size > 0
    assert (repo / "f").read_text().endswith("change\n")
    assert (repo / "u").exists()


def test_worktree_branch_protection_and_prune(tmp: Path) -> None:
    repo = init_repo(tmp / "worktree")
    commit_file(repo, "f", "x\n", "base")
    wt = tmp / "linked"
    git(repo, "worktree", "add", "-b", "topic", str(wt), "HEAD")
    assert git(repo, "branch", "-d", "topic", check=False).returncode != 0
    shutil.rmtree(wt)
    dry_proc = git(repo, "worktree", "prune", "--dry-run", "--verbose")
    dry = dry_proc.stdout + dry_proc.stderr
    assert "Removing" in dry and "linked" in dry
    git(repo, "worktree", "prune")
    assert str(wt) not in git(repo, "worktree", "list", "--porcelain").stdout


def test_conflict_stages(tmp: Path) -> None:
    repo = init_repo(tmp / "conflict")
    commit_file(repo, "f", "base\n", "base")
    git(repo, "switch", "-c", "side")
    commit_file(repo, "f", "side\n", "side")
    git(repo, "switch", "main")
    commit_file(repo, "f", "main\n", "main")
    proc = git(repo, "merge", "side", check=False)
    assert proc.returncode != 0
    stages = {line.split()[2] for line in git(repo, "ls-files", "-u", "--", "f").stdout.splitlines()}
    assert stages == {"1", "2", "3"}
    git(repo, "merge", "--abort")
    assert not git(repo, "ls-files", "-u").stdout


def test_unstage_preserves_worktree(tmp: Path) -> None:
    repo = init_repo(tmp / "undo")
    commit_file(repo, "f", "base\n", "base")
    (repo / "f").write_text("changed\n")
    git(repo, "add", "f")
    git(repo, "restore", "--staged", "--", "f")
    assert git(repo, "diff", "--cached", "--name-only").stdout == ""
    assert git(repo, "diff", "--name-only").stdout.strip() == "f"
    assert (repo / "f").read_text() == "changed\n"


def test_reflog_recovery(tmp: Path) -> None:
    repo = init_repo(tmp / "recover")
    base = commit_file(repo, "f", "base\n", "base")
    lost = commit_file(repo, "f", "base\nlost\n", "lost")
    git(repo, "reset", "--hard", base)
    assert lost in git(repo, "reflog", "show", "--all", "--format=%H").stdout
    git(repo, "branch", "recovery/lost", lost)
    assert git(repo, "rev-parse", "recovery/lost").stdout.strip() == lost


def test_cherry_pick_diverged_and_equivalent(tmp: Path) -> None:
    repo = init_repo(tmp / "pick")
    base = commit_file(repo, "f", "base\n", "base")
    git(repo, "switch", "-c", "source")
    source = commit_file(repo, "f", "base\nfix\n", "fix")
    git(repo, "switch", "-c", "dest", base)
    commit_file(repo, "other", "dest\n", "dest diverges")
    parent = git(repo, "rev-parse", "HEAD").stdout.strip()
    git(repo, "cherry-pick", source)
    new = git(repo, "rev-parse", "HEAD").stdout.strip()
    assert new != source
    assert git(repo, "rev-parse", "HEAD^").stdout.strip() == parent
    assert (repo / "f").read_text() == "base\nfix\n"
    # Replaying the same patch is empty and must be interpreted, not silently claimed successful.
    proc = git(repo, "cherry-pick", source, check=False)
    assert proc.returncode != 0
    assert git(repo, "status", "--porcelain").stdout == ""
    git(repo, "cherry-pick", "--abort")


def test_exact_force_with_lease_rejects_race(tmp: Path) -> None:
    remote = init_repo(tmp / "lease.git", bare=True)
    seed = init_repo(tmp / "lease-seed")
    commit_file(seed, "f", "base\n", "base")
    git(seed, "remote", "add", "origin", str(remote))
    git(seed, "push", "-u", "origin", "main")
    a, b = tmp / "lease-a", tmp / "lease-b"
    git(tmp, "clone", str(remote), str(a))
    git(tmp, "clone", str(remote), str(b))
    for repo in (a,b):
        git(repo, "config", "user.name", "Smoke")
        git(repo, "config", "user.email", "smoke@example.invalid")
    observed = git(a, "rev-parse", "origin/main").stdout.strip()
    commit_file(a, "a", "a\n", "a")
    commit_file(b, "b", "b\n", "b")
    git(b, "push", "origin", "main")
    proc = git(
        a, "push", "origin", "HEAD:refs/heads/main",
        f"--force-with-lease=refs/heads/main:{observed}",
        check=False,
    )
    assert proc.returncode != 0
    remote_tip = git(remote, "rev-parse", "refs/heads/main").stdout.strip()
    assert remote_tip == git(b, "rev-parse", "HEAD").stdout.strip()


def test_history_pickaxe(tmp: Path) -> None:
    repo = init_repo(tmp / "history")
    commit_file(repo, "f", "alpha\n", "base")
    added = commit_file(repo, "f", "alpha\nneedle\n", "add needle")
    found = git(repo, "log", "-Sneedle", "--format=%H", "--", "f").stdout.splitlines()
    assert found and found[0] == added


def test_bisect_oracle(tmp: Path) -> None:
    repo = init_repo(tmp / "bisect")
    commits = []
    for i in range(6):
        commits.append(commit_file(repo, "n", f"{i}\n", f"n={i}"))
    bad = commits[-1]
    good = commits[1]
    oracle = tmp / "oracle.sh"
    oracle.write_text("#!/bin/sh\nn=$(cat n)\n[ \"$n\" -lt 3 ]\n")
    oracle.chmod(0o755)
    git(repo, "bisect", "start", bad, good)
    proc = run(repo, "git", "bisect", "run", str(oracle), check=False)
    assert proc.returncode == 0
    out = proc.stdout + proc.stderr
    assert commits[3] in out
    git(repo, "bisect", "reset")
    assert git(repo, "rev-parse", "HEAD").stdout.strip() == bad


def test_tag_object_and_peeling(tmp: Path) -> None:
    repo = init_repo(tmp / "tag")
    target = commit_file(repo, "f", "x\n", "base")
    git(repo, "tag", "-a", "v1.0.0", "-m", "v1.0.0", target)
    assert git(repo, "cat-file", "-t", "refs/tags/v1.0.0").stdout.strip() == "tag"
    assert git(repo, "rev-parse", "refs/tags/v1.0.0^{}").stdout.strip() == target
    git(repo, "tag", "light", target)
    assert git(repo, "cat-file", "-t", "refs/tags/light").stdout.strip() == "commit"


def test_sparse_checkout(tmp: Path) -> None:
    repo = init_repo(tmp / "sparse")
    commit_file(repo, "services/api/a", "a\n", "api")
    commit_file(repo, "services/web/w", "w\n", "web")
    git(repo, "sparse-checkout", "init", "--cone")
    git(repo, "sparse-checkout", "set", "services/api")
    assert (repo / "services/api/a").exists()
    assert not (repo / "services/web/w").exists()
    assert git(repo, "show", "HEAD:services/web/w").stdout == "w\n"


def test_submodule_gitlink(tmp: Path) -> None:
    child = init_repo(tmp / "child")
    child_tip = commit_file(child, "c", "child\n", "child")
    parent = init_repo(tmp / "parent")
    commit_file(parent, "p", "parent\n", "parent")
    git(parent, "-c", "protocol.file.allow=always", "submodule", "add", str(child), "deps/child")
    git(parent, "commit", "-m", "add submodule")
    line = git(parent, "ls-files", "--stage", "--", "deps/child").stdout.strip()
    mode, oid, stage, path = line.split(maxsplit=3)
    assert mode == "160000" and oid == child_tip and stage == "0" and path == "deps/child"


def test_bundle_explicit_ref(tmp: Path) -> None:
    repo = init_repo(tmp / "bundle-src")
    tip = commit_file(repo, "f", "x\n", "base")
    bundle = tmp / "main.bundle"
    git(repo, "bundle", "create", str(bundle), "refs/heads/main")
    git(repo, "bundle", "verify", str(bundle))
    dst = tmp / "bundle-dst"
    git(tmp, "clone", str(bundle), str(dst))
    assert git(dst, "rev-parse", "refs/remotes/origin/main").stdout.strip() == tip
    git(dst, "switch", "-c", "main", "--track", "origin/main")
    assert git(dst, "rev-parse", "HEAD").stdout.strip() == tip


TESTS = [
    test_unborn_and_porcelain,
    test_config_origin,
    test_remote_redaction,
    test_atomic_commit_protects_unselected,
    test_branch_delete_proof,
    test_sync_fast_forward_and_divergence,
    test_merge_fast_forward,
    test_preservation_patch_does_not_clean,
    test_worktree_branch_protection_and_prune,
    test_conflict_stages,
    test_unstage_preserves_worktree,
    test_reflog_recovery,
    test_cherry_pick_diverged_and_equivalent,
    test_exact_force_with_lease_rejects_race,
    test_history_pickaxe,
    test_bisect_oracle,
    test_tag_object_and_peeling,
    test_sparse_checkout,
    test_submodule_gitlink,
    test_bundle_explicit_ref,
]


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="git-agent-skills-smoke-") as raw:
        base = Path(raw)
        for test in TESTS:
            case = base / test.__name__
            case.mkdir()
            try:
                test(case)
            except Exception as exc:
                print(f"FAIL: {test.__name__}: {exc}")
                return 1
            print(f"PASS: {test.__name__}")
    print(f"PASS: {len(TESTS)} local Git semantic smoke tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
