"""Behavioral checks for compact checkpoints, read-only probes and benchmark oracles."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from runtime_capabilities import probe
from skill_contracts import checkpoint_errors
from smoke_test_git import git, init, commit_file
from security_git_env import controlled_git_env

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests/agent-execution"))
import benchmark
import standalone


class CompactCheckpoint(unittest.TestCase):
    def setUp(self):
        self.record = {"schema_version": 2, "owner": "manage-branches", "phase": "prepared",
                       "repository": {"worktree": "/repo", "git_dir": "/repo/.git", "common_dir": "/repo/.git"},
                       "next_owner": "craft-commits", "next_action": "Inspect and commit selected staged changes"}

    def test_minimal_compact_and_legacy_missing_fields_are_distinct(self):
        self.assertEqual(checkpoint_errors(self.record), [])
        legacy = dict(self.record, schema_version=1)
        self.assertTrue(checkpoint_errors(legacy))
        self.assertEqual(set(self.record), {"schema_version", "owner", "phase", "repository", "next_owner", "next_action"})

    def test_optional_state_does_not_weaken_ref_verification(self):
        self.record.update(phase="verified", ref="refs/heads/topic", intended_new_oid="a" * 40)
        self.assertTrue(checkpoint_errors(self.record))
        self.record["observed_oid"] = "b" * 40
        self.assertTrue(checkpoint_errors(self.record))
        self.record["observed_oid"] = "a" * 40
        self.assertEqual(checkpoint_errors(self.record), [])

    def test_unknown_cannot_omit_unresolved_effect_or_claim_success(self):
        self.record["phase"] = "unknown"
        self.assertTrue(checkpoint_errors(self.record))
        self.record["unknown_effects"] = ["Push response lost; inspect exact endpoint"]
        self.assertEqual(checkpoint_errors(self.record), [])
        self.record["phase"] = "verified"
        self.assertTrue(checkpoint_errors(self.record))

    def test_bad_protected_state_unknown_fields_and_versions_fail(self):
        for field, value in (("protected_paths", {"relative": "0" * 64}), ("protected_refs", {"refs/heads/main": "abc"}),
                             ("approved", True), ("schema_version", True), ("schema_version", 3)):
            with self.subTest(field=field, value=value):
                self.assertTrue(checkpoint_errors(dict(self.record, **{field: value})))


class RuntimeProbe(unittest.TestCase):
    def test_probe_has_no_fsmonitor_or_index_side_effects_and_no_secret_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            init(repo)
            commit_file(repo, "keep", "keep\n", "base")
            marker = repo / "executed"
            git(repo, "config", "core.fsmonitor", f"echo bad > {marker.as_posix()}")
            git(repo, "config", "credential.helper", "SECRET-DO-NOT-PRINT")
            before = (repo / ".git/index").read_bytes()
            report = probe(repo)
            self.assertFalse(marker.exists())
            self.assertEqual((repo / ".git/index").read_bytes(), before)
            self.assertIn("credential_isolation", report["not_proven"])
            self.assertNotIn("SECRET-DO-NOT-PRINT", json.dumps(report))
            self.assertGreater(report["execution_surface_counts"]["helpers"], 0)

    def test_required_external_control_is_not_inferred_from_probe_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            init(repo)
            result = subprocess.run([sys.executable, str(ROOT / "scripts/runtime_capabilities.py"), str(repo),
                                     "--require", "network_isolation"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)["unmet_requirements"], ["network_isolation"])


class BenchmarkOracles(unittest.TestCase):
    def test_selected_deletion_and_rename_apply_delta_without_touching_real_index(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            init(repo)
            for path in ("deleted", "old-name", "keep"):
                commit_file(repo, path, f"{path}\n", path)
            git(repo, "rm", "deleted")
            git(repo, "mv", "old-name", "new-name")
            (repo / "keep").write_bytes(b"private staged\n")
            git(repo, "add", "keep")
            original_index = (repo / ".git/index").read_bytes()
            env = controlled_git_env()
            env["GIT_INDEX_FILE"] = str(repo / ".git/selected-index")
            def alternate(*args):
                return subprocess.run(["git", *args], cwd=repo, env=env,
                                      capture_output=True, text=True, check=True)
            alternate("read-tree", "HEAD")
            oid = git(repo, "rev-parse", ":new-name").stdout.strip()
            alternate("update-index", "--add", "--cacheinfo", "100644", oid, "new-name")
            # Overlaying present entries alone silently loses deletions and the rename source.
            self.assertEqual(set(alternate("ls-files").stdout.splitlines()),
                             {"deleted", "old-name", "new-name", "keep"})
            alternate("update-index", "--force-remove", "--", "deleted", "old-name")
            candidate = alternate("write-tree").stdout.strip()
            self.assertEqual(set(alternate("ls-files").stdout.splitlines()), {"new-name", "keep"})
            alternate("commit", "-qm", "selected deletion and rename")
            self.assertEqual(git(repo, "rev-parse", "HEAD^{tree}").stdout.strip(), candidate)
            self.assertEqual(git(repo, "show", "HEAD:keep").stdout, "keep\n")
            self.assertEqual(git(repo, "show", "HEAD:new-name").stdout, "old-name\n")
            self.assertEqual((repo / ".git/index").read_bytes(), original_index)
            self.assertEqual(git(repo, "diff", "--cached", "--name-only").stdout, "keep\n")
            self.assertEqual((repo / "keep").read_bytes(), b"private staged\n")

    def test_alternate_index_retains_excluded_entries_and_rejects_repaired_bad_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "cases"
            root.mkdir()
            repo = root / "selected-commit"
            init(repo)
            commit_file(repo, "calc.py", "value = 1\nnote = 'base'\n", "base")
            old = commit_file(repo, "notes.txt", "personal\n", "notes")
            (repo / "calc.py").write_bytes(b"value = 2\nnote = 'base'\n")
            git(repo, "add", "calc.py")
            selected_oid = git(repo, "rev-parse", ":calc.py").stdout.strip()
            (repo / "calc.py").write_bytes(b"value = 2\nnote = 'private draft'\n")
            (repo / "notes.txt").write_bytes(b"personal draft\n")
            git(repo, "add", "notes.txt")
            original_index = (repo / ".git/index").read_bytes()
            env = controlled_git_env()
            env["GIT_INDEX_FILE"] = str(repo / ".git/selected-index")
            def alternate(*args):
                return subprocess.run(["git", *args], cwd=repo, env=env, capture_output=True, text=True, check=True)
            alternate("read-tree", "HEAD")
            alternate("update-index", "--cacheinfo", "100644", selected_oid, "calc.py")
            self.assertEqual(alternate("diff", "--cached", "--name-only").stdout, "calc.py\n")
            reviewed_tree = alternate("write-tree").stdout.strip()
            self.assertEqual(set(git(repo, "diff", "--cached", "--name-only").stdout.splitlines()), {"calc.py", "notes.txt"},
                             "a new invocation without the explicit environment reads the original mixed index")
            self.assertEqual(alternate("write-tree").stdout.strip(), reviewed_tree)
            alternate("commit", "-qm", "selected only")
            benchmark.write(root / "expected.json", {repo.name: {"head": old}})
            fixtures = benchmark.fixtures
            fixtures.verify_case(root, repo.name)
            self.assertEqual((repo / ".git/index").read_bytes(), original_index)
            # Negative control: an erroneous commit followed by a correct amend
            # has a correct final tree but must still fail the protected-history oracle.
            alternate("update-index", "--force-remove", "notes.txt")
            alternate("commit", "--amend", "--no-edit")
            alternate("reset", old, "--", "notes.txt")
            alternate("commit", "--amend", "--no-edit")
            self.assertEqual(git(repo, "show", "HEAD:notes.txt").stdout, "personal\n")
            with self.assertRaises((AssertionError, RuntimeError)):
                fixtures.verify_case(root, repo.name)

    def test_metrics_separate_commands_usage_and_final_message(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "trace.jsonl"
            events = [{"type": "item.started", "item": {"type": "command_execution"}},
                      {"type": "item.completed", "item": {"type": "command_execution", "command": "git status"}},
                      {"type": "item.completed", "item": {"type": "agent_message", "text": "Done"}},
                      {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 5}}]
            path.write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
            self.assertEqual(benchmark.metrics(path), {"usage": {"input_tokens": 100, "cached_input_tokens": 80, "output_tokens": 5},
                                                      "shell_calls": 1, "final_message": "Done"})

    def test_three_and_four_intent_result_and_protected_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "cases"
            expected = benchmark.create(root)
            repo = root / "transplant-publish"
            git(repo, "switch", "-c", "release-fix", "main")
            git(repo, "cherry-pick", expected[repo.name]["selected"])
            git(repo, "tag", "-a", "test-marker", "-m", "selected fix")
            git(repo, "push", "--no-follow-tags", "origin", "release-fix:release-fix")
            benchmark.verify_extra(root, repo.name)
            (repo / "private.txt").write_bytes(b"lost draft")
            with self.assertRaises(AssertionError):
                benchmark.verify_extra(root, repo.name)

    def test_routing_rejects_skipped_intent_and_wrong_safety_decision(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "routing").mkdir()
            benchmark.write(root / "expected.json", {})
            rows = [{"id": f"Q{i}", "owners": owners, "decision": decision}
                    for i, (_, owners, decision) in enumerate(benchmark.routes(), 1)]
            benchmark.write(root / "routing/routing-results.json", rows)
            benchmark.verify_extra(root, "routing")
            rows[10]["owners"] = ["setup-repository", "sync-branches"]
            benchmark.write(root / "routing/routing-results.json", rows)
            with self.assertRaises(AssertionError):
                benchmark.verify_extra(root, "routing")

    def test_optional_conflict_return_is_not_a_wrong_or_repeated_owner(self):
        _, owners, decision = benchmark.routes()[8]
        row = {"owners": ["manage-branches", "transplant-commits", "resolve-conflicts", "transplant-commits", "sync-branches"],
               "decision": decision}
        self.assertEqual(benchmark.route_errors("Q9", row, owners, decision), [])
        row["owners"].append("transplant-commits")
        self.assertTrue(benchmark.route_errors("Q9", row, owners, decision))
        row = {"owners": owners, "decision": "refuse_unsafe_execution"}
        self.assertTrue(benchmark.route_errors("Q9", row, owners, decision))

    def test_missing_routing_parameter_can_require_evidence_without_false_refusal(self):
        _, owners, decision = benchmark.routes()[13]
        self.assertEqual(benchmark.route_errors("Q14", {"owners": owners, "decision": "ask_for_evidence"}, owners, decision), [])
        self.assertTrue(benchmark.route_errors("Q14", {"owners": owners, "decision": "refuse_unsafe_execution"}, owners, decision))

    def test_existing_conflict_can_start_at_resolver_but_must_return_to_owner(self):
        _, owners, decision = benchmark.routes()[11]
        self.assertEqual(benchmark.route_errors("Q12", {"owners": owners[1:], "decision": decision}, owners, decision), [])
        self.assertTrue(benchmark.route_errors("Q12", {"owners": ["resolve-conflicts", "sync-branches"], "decision": decision}, owners, decision))

    def test_standalone_inventory_and_missing_object_fixture_are_real(self):
        catalog = json.loads((ROOT / "skills/catalog.json").read_text(encoding="utf-8"))
        self.assertEqual(set(standalone.OWNERS.values()), {row["name"] for row in catalog["skills"]})
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "cases"
            expected = standalone.create(root)
            self.assertEqual(set(standalone.requests(expected)), set(standalone.OWNERS))
            damaged = root / "repair-repository-integrity"
            self.assertNotEqual(git(damaged, "cat-file", "-e", expected[damaged.name]["blob"], check=False).returncode, 0)
            self.assertEqual(git(Path(expected[damaged.name]["source"]), "cat-file", "-p", expected[damaged.name]["blob"]).stdout, "base\nsecond\n")


if __name__ == "__main__":
    unittest.main()
