#!/usr/bin/env python3
"""Behavioral checks for the v2 review fixes; no agent-performance claims."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from smoke_test_git import commit_file, git, init, load_helper
from security_git_env import controlled_git_env, resolve_git


class ReviewRegressions(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="git-review-regression-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.environment = patch.dict(os.environ, controlled_git_env(), clear=True)
        self.environment.start()
        self.addCleanup(self.environment.stop)

    def repo(self, name):
        p = self.root / name
        init(p)
        return p

    def helper(self):
        return load_helper("skills/manage-remotes/scripts/inspect_remotes.py", "review_remote_helper")

    def test_unicode_endpoint_records(self):
        p = self.repo("repo")
        helper = self.helper()
        for separator in ("\u0085", "\u2028", "\u2029"):
            with self.subTest(separator=repr(separator)):
                url = "https://one.example/repo" + separator + "https://two.example/repo"
                git(p, "config", "remote.origin.url", url)
                urls = helper.inspect(p)["remotes"]["origin"]["effective_fetch"]
                self.assertEqual(len(urls), 1)
                self.assertEqual(urls[0], {"display": url, "classified": True})

    def test_helper_repository_selectors(self):
        a, b = self.repo("a"), self.repo("b")
        git(a, "remote", "add", "origin", "https://a.example/repo")
        git(b, "remote", "add", "origin", "https://b.example/repo")
        with patch.dict(os.environ, {"GIT_DIR": str(a / ".git"),
                                    "GIT_COMMON_DIR": str(a / ".git"),
                                    "GIT_WORK_TREE": str(a)}):
            data = self.helper().inspect(b)
        self.assertEqual(Path(data["repository"]), b.resolve())
        self.assertEqual(data["remotes"]["origin"]["effective_fetch"][0]["display"],
                         "https://b.example/repo")

    def test_helper_ignores_config_file_selector(self):
        p = self.repo("repo")
        git(p, "remote", "add", "origin", "https://repo.example/repo")
        unrelated = self.root / "unrelated.config"
        unrelated.write_text('[remote "other"]\n\turl = https://other.example/repo\n',
                             encoding="utf-8")
        for selected in (unrelated, self.root / "missing.config"):
            overrides = {"GIT_CONFIG": str(selected), "GIT_CONFIG_COUNT": "1",
                         "GIT_CONFIG_KEY_0": "remote.origin.pushurl",
                         "GIT_CONFIG_VALUE_0": "https://push.example/repo"}
            with self.subTest(selected=selected), patch.dict(os.environ, overrides):
                remote = self.helper().inspect(p)["remotes"]
                self.assertEqual(set(remote), {"origin"})
                self.assertEqual(remote["origin"]["url"][0]["display"],
                                 "https://repo.example/repo")
                self.assertEqual(remote["origin"]["effective_fetch"][0]["display"],
                                 "https://repo.example/repo")
                self.assertEqual(remote["origin"]["pushurl"][0]["scope"], "command")
                self.assertEqual(remote["origin"]["effective_push"][0]["display"],
                                 "https://push.example/repo")

    def test_scp_grammar_and_redaction(self):
        helper = self.helper()
        for url, display in (
            ("host.example:org/repo.git", "host.example:org/repo.git"),
            ("git@host.example:org/repo.git", "@host.example:org/repo.git"),
            ("[::1]:org/repo.git", "[::1]:org/repo.git"),
            ("git@[::1]:org/repo.git", "@[::1]:org/repo.git"),
            ("./host:repo.git", "./host:repo.git"),
            ("ssh://user:secret@host.example/repo?token=secret#secret",
             "ssh://@host.example/repo"),
        ):
            with self.subTest(url=url):
                self.assertEqual(helper.sanitize_url(url), {"display": display, "classified": True})
        for url in ("ext::secret command", "custom://user:secret@host/repo",
                    "https://[broken", "host:repo\nsecret", "host:repo\x00secret"):
            with self.subTest(url=url):
                self.assertEqual(helper.sanitize_url(url), {"display": "", "classified": False})

    def test_remote_push_refspec_inventory(self):
        p = self.repo("repo")
        git(p, "config", "remote.origin.url", "https://example.invalid/repo.git")
        refspec = "+refs/heads/*:refs/heads/*"
        git(p, "config", "remote.origin.push", refspec)
        remote = self.helper().inspect(p)["remotes"]["origin"]
        self.assertEqual([item["value"] for item in remote["push"]], [refspec])

    def test_explicit_zero_port_is_preserved(self):
        helper = self.helper()
        url = "https://example.invalid:0/repo.git"
        self.assertEqual(helper.sanitize_url(url), {"display": url, "classified": True})

    def bare(self, name):
        p = self.root / name
        git(self.root, "init", "-q", "--bare", str(p))
        return p

    def nested(self):
        source, parent = self.repo("nested-source"), self.repo("parent")
        commit_file(source, "file.txt", "base\n", "base")
        git(source, "branch", "-M", "main")
        destination = self.bare("nested.git")
        git(source, "remote", "add", "origin", str(destination))
        git(source, "push", "origin", "main:main")
        git(destination, "symbolic-ref", "HEAD", "refs/heads/main")
        commit_file(parent, "top", "top\n", "top")
        git(parent, "branch", "-M", "main")
        git(parent, "-c", "protocol.file.allow=always", "submodule", "add",
            str(destination), "nested")
        git(parent, "commit", "-qm", "nested")
        nested = parent / "nested"
        git(nested, "config", "user.name", "Test User")
        git(nested, "config", "user.email", "test@example.invalid")
        return parent, nested, destination

    def test_chained_rewrite_named_invocation(self):
        p = self.repo("work")
        oid = commit_file(p, "data", "base\n", "base")
        approved, other = self.bare("approved.git"), self.bare("other.git")
        git(p, "remote", "add", "origin", "alias:repo")
        git(p, "config", f"url.{approved.as_posix()}.insteadOf", "alias:repo")
        git(p, "config", f"url.{other.as_posix()}.insteadOf", approved.as_posix())
        expanded = git(p, "remote", "get-url", "--push", "origin").stdout.strip()
        self.assertEqual(expanded, approved.as_posix())
        git(p, "push", "--no-follow-tags", "--no-recurse-submodules", "origin",
            f"{oid}:refs/heads/reviewed")
        self.assertEqual(git(approved, "rev-parse", "refs/heads/reviewed").stdout.strip(), oid)
        self.assertNotEqual(git(other, "show-ref", "--verify", "refs/heads/reviewed", check=False).returncode, 0)
        self.assertIn(oid, git(p, "ls-remote", "origin", "refs/heads/reviewed").stdout)
        # Negative control: reusing the expanded URL applies another rewrite.
        git(p, "push", "--no-follow-tags", "--no-recurse-submodules", expanded,
            f"{oid}:refs/heads/negative-control")
        self.assertEqual(git(other, "rev-parse", "refs/heads/negative-control").stdout.strip(), oid)

    def test_parent_push_does_not_publish_nested_refs(self):
        parent, nested, remote = self.nested()
        old = git(remote, "rev-parse", "main").stdout.strip()
        commit_file(nested, "file.txt", "new\n", "nested update")
        git(parent, "add", "nested")
        git(parent, "commit", "-qm", "gitlink")
        destination = self.bare("parent.git")
        git(parent, "remote", "add", "origin", str(destination))
        git(parent, "config", "push.recurseSubmodules", "on-demand")
        rejected = git(parent, "push", "--no-follow-tags", "--recurse-submodules=check",
                       "origin", "main:main", check=False)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertEqual(git(remote, "rev-parse", "main").stdout.strip(), old)
        # Test the effect bound itself; application guidance must also establish
        # collaborator availability before declaring the parent publication usable.
        git(parent, "push", "--no-follow-tags", "--no-recurse-submodules", "origin", "main:main")
        self.assertEqual(git(remote, "rev-parse", "main").stdout.strip(), old)

    def test_observation_fetch_does_not_recurse_into_submodules(self):
        parent, nested, remote = self.nested()
        observers = {}
        for name in ("ambient-recursion", "bounded"):
            observer = self.root / name
            git(self.root, "clone", "-q", str(parent), str(observer))
            git(observer, "-c", "protocol.file.allow=always", "submodule", "update", "--init")
            git(observer, "config", "fetch.recurseSubmodules", "true")
            observers[name] = observer
        original = git(remote, "rev-parse", "main").stdout.strip()
        updated = commit_file(nested, "file.txt", "updated\n", "nested update")
        git(nested, "push", "origin", "HEAD:main")
        git(parent, "add", "nested")
        git(parent, "commit", "-qm", "gitlink update")
        branch_refspec = "refs/heads/main:refs/observations/main"
        for name, observer in observers.items():
            flags = ["--no-recurse-submodules"] if name == "bounded" else []
            git(observer, "-c", "protocol.file.allow=always", "fetch", "--no-tags",
                *flags, str(parent), branch_refspec)
        self.assertEqual(git(observers["ambient-recursion"] / "nested", "rev-parse",
                             "refs/remotes/origin/main").stdout.strip(), updated)
        self.assertEqual(git(observers["bounded"] / "nested", "rev-parse",
                             "refs/remotes/origin/main").stdout.strip(), original)

    def test_symbolic_tag_no_dereference_preserves_branch(self):
        p = self.repo("repo")
        oid = commit_file(p, "data", "base\n", "base")
        branch = git(p, "symbolic-ref", "HEAD").stdout.strip()
        git(p, "symbolic-ref", "refs/tags/alias", branch)
        self.assertEqual(git(p, "symbolic-ref", "refs/tags/alias").stdout.strip(), branch)
        git(p, "update-ref", "--no-deref", "-d", "refs/tags/alias", oid)
        self.assertEqual(git(p, "rev-parse", branch).stdout.strip(), oid)
        self.assertNotEqual(git(p, "symbolic-ref", "refs/tags/alias", check=False).returncode, 0)
        git(p, "tag", "direct", oid)
        git(p, "update-ref", "--no-deref", "-d", "refs/tags/direct", oid)
        self.assertEqual(git(p, "rev-parse", branch).stdout.strip(), oid)

    def test_symbolic_tag_transaction_requires_old_target(self):
        p = self.repo("repo")
        oid = commit_file(p, "data", "base\n", "base")
        branch = git(p, "symbolic-ref", "HEAD").stdout.strip()
        git(p, "symbolic-ref", "refs/tags/transaction", branch)
        def transaction(target):
            return subprocess.run([resolve_git(), "update-ref", "--stdin", "--no-deref"],
                                  input=f"start\nsymref-delete refs/tags/transaction {target}\nprepare\ncommit\n",
                                  cwd=p, env=controlled_git_env(), text=True,
                                  capture_output=True, timeout=30)
        stale = transaction("refs/heads/wrong-target")
        self.assertNotEqual(stale.returncode, 0)
        self.assertEqual(git(p, "symbolic-ref", "refs/tags/transaction").stdout.strip(), branch)
        if "unknown command" in stale.stderr:
            # Older Git cannot perform the authorized symbolic-target CAS;
            # guidance requires stopping that path, not falling back to OID CAS.
            self.compatibility_outcome = "safe_refusal"
            return
        self.assertEqual(transaction(branch).returncode, 0)
        self.assertEqual(git(p, "rev-parse", branch).stdout.strip(), oid)
        self.assertNotEqual(git(p, "symbolic-ref", "refs/tags/transaction", check=False).returncode, 0)

    def test_status_fsmonitor_disabled(self):
        p = self.repo("repo")
        commit_file(p, "data", "base\n", "base")
        marker, hook = p / "executed", p / "monitor"
        hook.write_text('#!/bin/sh\nprintf ran > "' + marker.as_posix() + '"\nprintf "1\\000"\n')
        hook.chmod(0o700)
        env = controlled_git_env()
        env["GIT_CONFIG_VALUE_0"] = hook.as_posix()
        def inspect(command, *flags):
            return subprocess.run([resolve_git(), *flags, "--no-optional-locks", *command], cwd=p, env=env,
                                  capture_output=True, timeout=30, check=True)
        inspect(["status", "--porcelain=v2", "--branch"])
        self.assertTrue(marker.exists())
        marker.unlink()
        # Even an inventory command may read the index and invoke the monitor.
        inspect(["ls-files", "-u"])
        self.assertTrue(marker.exists())
        marker.unlink()
        for command in (["status", "--porcelain=v2", "--branch"], ["ls-files", "-u"],
                        ["ls-files", "-v", "-z"], ["diff"], ["diff", "--cached"]):
            inspect(command, "-c", "core.fsmonitor=false")
            self.assertFalse(marker.exists())

    def test_worktree_config_migration(self):
        p = self.repo("main")
        commit_file(p, "data", "base\n", "base")
        linked = self.root / "linked"
        git(p, "worktree", "add", "--detach", str(linked))
        git(p, "config", "core.worktree", str(p))
        config = p / ".git" / "config.worktree"
        git(p, "config", "--file", str(config), "core.worktree", str(p))
        git(p, "config", "--unset", "core.worktree")
        git(p, "config", "extensions.worktreeConfig", "true")
        git(linked, "config", "--worktree", "user.email", "linked@example.invalid")
        self.assertEqual(Path(git(linked, "rev-parse", "--show-toplevel").stdout.strip()), linked)
        self.assertEqual(Path(git(p, "rev-parse", "--show-toplevel").stdout.strip()), p)
        self.assertEqual(git(linked, "rev-parse", "--is-bare-repository").stdout.strip(), "false")

    def test_staged_conflict_check(self):
        p = self.repo("repo")
        commit_file(p, "data", "base\n", "base")
        (p / "data").write_text("<<<<<<< HEAD\na\n=======\nb\n>>>>>>> topic\n")
        git(p, "add", "data")
        self.assertEqual(git(p, "diff", "--check", check=False).returncode, 0)
        self.assertNotEqual(git(p, "diff", "--cached", "--check", check=False).returncode, 0)

    def test_raw_backup_before_clearing_stash(self):
        p = self.repo("repo")
        commit_file(p, ".gitattributes", "*.txt text eol=lf\n", "attributes")
        source, backup = p / "notes.txt", self.root / "raw-backup"
        source.write_bytes(b"new\r\n")
        shutil.copyfile(source, backup)
        self.assertEqual(backup.read_bytes(), source.read_bytes())
        git(p, "stash", "push", "-u")
        self.assertFalse(source.exists())
        git(p, "stash", "apply")
        self.assertEqual(source.read_bytes(), b"new\n")
        self.assertEqual(backup.read_bytes(), b"new\r\n")

    def test_restack_disables_notes_rewriting(self):
        p = self.repo("repo")
        base = commit_file(p, "data", "base\n", "base")
        git(p, "checkout", "-b", "child")
        child = commit_file(p, "child", "child\n", "child")
        git(p, "notes", "add", "-m", "note", child)
        notes = git(p, "rev-parse", "refs/notes/commits").stdout.strip()
        git(p, "checkout", "--detach", base)
        new_parent = commit_file(p, "parent", "parent\n", "parent")
        git(p, "config", "notes.rewriteRef", "refs/notes/commits")
        env = controlled_git_env()
        env["GIT_NOTES_REWRITE_REF"] = "refs/notes/commits"
        subprocess.run([resolve_git(), "-c", "rebase.updateRefs=false", "-c", "notes.rewrite.rebase=false",
                        "rebase", "--onto", new_parent, base, "child"],
                       cwd=p, env=env, capture_output=True, timeout=30, check=True)
        self.assertEqual(git(p, "rev-parse", "refs/notes/commits").stdout.strip(), notes)

    def test_parent_only_local_submodule_operations(self):
        parent, nested, _ = self.nested()
        git(parent, "config", "submodule.recurse", "true")
        git(parent, "config", "submodule.nested.ignore", "all")
        source = nested / "file.txt"
        source.write_bytes(b"retain\n")
        self.assertEqual(git(parent, "status", "--porcelain=v2").stdout, "")
        git(parent, "reset", "--hard", "--no-recurse-submodules", "HEAD")
        self.assertEqual(source.read_bytes(), b"retain\n")
        git(parent, "config", "submodule.propagateBranches", "true")
        git(parent, "-c", "submodule.recurse=false", "branch", "parent-only", "HEAD")
        self.assertNotEqual(git(nested, "show-ref", "--verify", "refs/heads/parent-only", check=False).returncode, 0)

    def test_observation_fetch_without_auto_tags(self):
        source = self.repo("source")
        oid = commit_file(source, "data", "base\n", "base")
        branch = git(source, "symbolic-ref", "--short", "HEAD").stdout.strip()
        git(source, "tag", "unexpected", oid)
        for name, flags in (("bounded", ["--no-tags"]), ("negative", [])):
            observer = self.repo(name)
            git(observer, "fetch", *flags, str(source), f"refs/heads/{branch}:refs/observations/selected")
            exists = git(observer, "show-ref", "--verify", "refs/tags/unexpected", check=False).returncode == 0
            self.assertEqual(exists, name == "negative")

    def test_explicit_fetch_refspec_still_uses_remote_refmap(self):
        source = self.repo("source")
        oid = commit_file(source, "data", "base\n", "base")
        branch = git(source, "symbolic-ref", "--short", "HEAD").stdout.strip()
        for name, flags in (("ambient-refmap", []), ("bounded", ["--refmap="])):
            observer = self.repo(name)
            git(observer, "remote", "add", "origin", str(source))
            git(observer, "fetch", "--no-tags", "--no-recurse-submodules", *flags,
                "origin", f"refs/heads/{branch}:refs/observations/selected")
            self.assertEqual(git(observer, "rev-parse", "refs/observations/selected").stdout.strip(), oid)
            tracking_exists = git(observer, "show-ref", "--verify",
                                  f"refs/remotes/origin/{branch}", check=False).returncode == 0
            self.assertEqual(tracking_exists, name == "ambient-refmap")

    def test_recovery_intrinsic_content(self):
        p = self.repo("repo")
        original = commit_file(p, "lost.txt", "original\n", "original")
        replacement = commit_file(p, "lost.txt", "wanted\n", "replacement")
        git(p, "replace", original, replacement)
        git(p, "update-ref", "refs/recovery/example", original, "0" * len(original))
        env = controlled_git_env()
        env.pop("GIT_NO_REPLACE_OBJECTS", None)
        def read(*flags):
            return subprocess.run([resolve_git(), *flags, "show", "refs/recovery/example:lost.txt"],
                                  cwd=p, env=env, capture_output=True, timeout=30, check=True).stdout
        self.assertEqual(read(), b"wanted\n")
        self.assertEqual(read("--no-replace-objects"), b"original\n")
        git(p, "update-ref", "refs/recovery/replacement", replacement, "0" * len(replacement))
        self.assertEqual(git(p, "--no-replace-objects", "show", "refs/recovery/replacement:lost.txt").stdout, "wanted\n")

    def test_worktree_hidden_edits_are_preserved(self):
        p = self.repo("main")
        commit_file(p, "file.txt", "base\n", "base")
        w = self.root / "linked"
        git(p, "worktree", "add", "--detach", str(w))
        git(w, "update-index", "--assume-unchanged", "file.txt")
        source, backup = w / "file.txt", self.root / "raw-backup"
        source.write_bytes(b"retain\n")
        self.assertEqual(git(w, "status", "--porcelain=v2").stdout, "")
        self.assertIn("h file.txt\0", git(w, "ls-files", "-v", "-z").stdout)
        shutil.copyfile(source, backup)
        self.assertEqual(source.read_bytes(), backup.read_bytes())
        git(p, "worktree", "remove", str(w))
        self.assertEqual(backup.read_bytes(), b"retain\n")

    def test_exact_config_value_selector(self):
        p = self.repo("repo")
        selected, retained = "https://host.example/a.b.git", "https://hostXexample/aXbXgit"
        for value in (selected, retained):
            git(p, "config", "--add", "test.multivalue", value)
        git(p, "config", "--fixed-value", "--unset-all", "test.multivalue", selected)
        self.assertEqual(git(p, "config", "--get-all", "test.multivalue").stdout.strip(), retained)


class CompatibilityResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.safe_refusals = []

    def addSuccess(self, test):
        if getattr(test, "compatibility_outcome", None) == "safe_refusal":
            self.safe_refusals.append(test.id())
            self.stream.writeln("SAFE_REFUSAL (symbolic-target transaction unavailable; refs preserved)")
        else:
            super().addSuccess(test)


if __name__ == "__main__":
    program = unittest.main(verbosity=2, exit=False,
                            testRunner=unittest.TextTestRunner(verbosity=2, resultclass=CompatibilityResult))
    result = program.result
    unsupported = len(result.skipped)
    failed = len(result.failures) + len(result.errors)
    refused = len(result.safe_refusals)
    print(f"COMPATIBILITY supported={result.testsRun - unsupported - failed - refused} "
          f"safe_refusal={refused} unsupported={unsupported} failed={failed}")
    sys.exit(0 if result.wasSuccessful() and not unsupported else 1)
