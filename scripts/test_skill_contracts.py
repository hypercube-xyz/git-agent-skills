"""Routing responsibility must not be conflated with permission to execute."""
import json
import copy
import sys
import tempfile
import subprocess
import unittest
from pathlib import Path

from skill_contracts import checkpoint_errors, routing_errors
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests/agent-execution"))
import composition
from smoke_test_git import git

ROOT = Path(__file__).resolve().parents[1]


class RoutingSemantics(unittest.TestCase):
    def test_conditional_preparation_is_not_an_extra_unconditional_mutation(self):
        expected = {"owners": ["craft-commits", "sync-branches"], "decision": "evaluate"}
        row = {"owners": ["craft-commits", "preserve-work", "craft-commits", "sync-branches"],
               "decision": "evaluate", "steps": [
                   {"owner": "craft-commits", "phase": "inspect", "when": "always"},
                   {"owner": "preserve-work", "phase": "execute", "when": "if_needed_to_preserve_work"},
                   {"owner": "craft-commits", "phase": "execute", "when": "after_verified_previous_step"},
                   {"owner": "sync-branches", "phase": "execute", "when": "after_verified_previous_step"}]}
        composition.verify_route("R7", row, expected)
        row["steps"][1]["when"] = "always"
        with self.assertRaisesRegex(AssertionError, "unconditional"):
            composition.verify_route("R7", row, expected)
        row["steps"][1]["when"] = "if_needed_to_preserve_work"
        row["steps"].append({"owner": "sync-branches", "phase": "execute", "when": "always"})
        with self.assertRaisesRegex(AssertionError, "restarted"):
            composition.verify_route("R7", row, expected)
    def test_legacy_fixture_shape_remains_accepted(self):
        legacy = {"schema_version": 1, "cases": [{"id": "legacy", "skill": "sync-branches", "expect": "route", "prompt": "Push this branch"}]}
        self.assertEqual(routing_errors(legacy, {"sync-branches"}), [])

    def test_no_unrequested_commit_or_publication_in_workflow(self):
        document = {"workflows": [{"id": "bad", "steps": [
            {"owner": "find-regression", "phase": "execute", "when": "oracle verified"},
            {"owner": "craft-commits", "phase": "execute", "when": "search finished"}],
            "forbidden_unrequested_steps": ["craft-commits"]}]}
        self.assertTrue(any("unrequested step" in error for error in routing_errors(document, {"find-regression", "craft-commits"})))

    def test_invalid_decision_and_duplicate_restart_are_rejected(self):
        document = {"decision_schema_version": 1, "cases": [{"id": "invalid", "expect": "route", "decision": "authorized"}],
                    "workflows": [{"id": "repeat", "steps": [{"owner": "sync-branches", "phase": "execute", "when": "inspected"}] * 2}]}
        errors = routing_errors(document, {"sync-branches"})
        self.assertTrue(any("execution decision" in value for value in errors))
        self.assertTrue(any("duplicate owner/phase" in value for value in errors))
    def test_unsafe_conflict_request_routes_to_its_owner(self):
        document = json.loads((ROOT / "tests/routing.json").read_text(encoding="utf-8"))
        case = next(row for row in document["cases"]
                    if row["prompt"] == "Choose ours for every conflict without inspecting semantics.")
        self.assertEqual(case["expect"], "route")
        self.assertEqual(case["decision"], "refuse_unsafe_execution")

    def test_find_then_fix_preserves_both_requested_steps(self):
        document = json.loads((ROOT / "tests/routing.json").read_text(encoding="utf-8"))
        case = next(row for row in document["cases"]
                    if row["prompt"] == "Fix the regression after you find it.")
        self.assertEqual(case["expect"], "route")
        plan = next(row for row in document["workflows"] if row["prompt"] == case["prompt"])
        self.assertEqual([step["owner"] for step in plan["steps"]],
                         ["find-regression", "external:code-repair"])
        self.assertIn("craft-commits", plan["forbidden_unrequested_steps"])


class NativeHandoffResume(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="skill-composition-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name).resolve() / "cases"
        composition.create(cls.root)
        cls.expected = json.loads((cls.root / "expected.json").read_text())

    def protected(self, record):
        repo = Path(record["repository"]["worktree"])
        for path, digest in record["protected_paths"].items():
            self.assertEqual(composition.sha(Path(path)), digest)
        for ref, oid in record["protected_refs"].items():
            self.assertEqual(git(repo, "rev-parse", ref).stdout.strip(), oid)

    def test_success_returns_index_to_owner_then_publishes(self):
        p = self.root / "merge-resume"
        evidence = self.expected[p.name]
        record = evidence["checkpoint"]
        self.assertEqual(checkpoint_errors(record), [])
        self.assertEqual((p / ".git/MERGE_HEAD").read_text().strip(), record["operation"]["source_oid"])
        (p / "settings.txt").write_bytes(b"timeout=20\nretries=3\n")
        git(p, "add", "--", "settings.txt")
        reviewed_tree = git(p, "write-tree").stdout.strip()
        record = copy.deepcopy(record)
        record.update(owner="resolve-conflicts", phase="verified", next_owner="integrate-branches")
        record["verified_effects"] = [{"kind": "index", "target": "reviewed staged tree", "value": reviewed_tree}]
        self.assertEqual(checkpoint_errors(record), [])
        # The integration owner completes the existing merge, not a fresh merge.
        git(p, "commit", "-qm", "combine settings")
        self.assertEqual(git(p, "rev-parse", "HEAD^{tree}").stdout.strip(), reviewed_tree)
        parents = git(p, "rev-list", "--parents", "-n", "1", "HEAD").stdout.split()
        self.assertEqual(parents[1:], [evidence["old"], evidence["source"]])
        self.protected(record)
        git(p, "push", "--no-follow-tags", "--no-recurse-submodules", "origin", "HEAD:refs/heads/main")
        self.assertEqual(git(self.root / "merge.git", "rev-parse", "main").stdout.strip(), parents[0])

    def test_interrupted_restack_resumes_only_pending_layer(self):
        p = self.root / "restack-resume"
        evidence = self.expected[p.name]
        journal = json.loads((p / ".git/handoff.json").read_text())
        for record in journal:
            self.assertEqual(checkpoint_errors(record), [])
        self.assertEqual(git(p, "rev-parse", "B").stdout.strip(), journal[0]["intended_new_oid"])
        self.assertEqual(git(p, "rev-parse", "REBASE_HEAD").stdout.strip(), journal[1]["operation"]["source_oid"])
        (p / "settings.txt").write_bytes(b"main\nC\n")
        git(p, "add", "--", "settings.txt")
        git(p, "-c", "rebase.updateRefs=false", "-c", "notes.rewrite.rebase=false", "rebase", "--continue")
        self.assertEqual(git(p, "rev-parse", "C^").stdout.strip(), evidence["new_b"])
        self.assertEqual(composition.sha(p / ".git/logs/refs/heads/B"), evidence["b_reflog_sha256"])
        self.protected(journal[1])

    def test_lost_response_reconciles_to_noop(self):
        p = self.root / "retry-noop"
        evidence = self.expected[p.name]
        record = copy.deepcopy(evidence["checkpoint"])
        self.assertEqual(checkpoint_errors(record), [])
        remote_oid = git(p, "ls-remote", "origin", "refs/heads/main").stdout.split()[0]
        self.assertEqual(remote_oid, record["intended_new_oid"])
        record.update(phase="verified", observed_oid=remote_oid, unknown_effects=[], next_action="Publication already complete; no retry")
        self.assertEqual(checkpoint_errors(record), [])
        self.assertEqual(composition.sha(p / ".git/index"), evidence["index_sha256"])
        self.assertEqual(composition.sha(p / ".git/logs/refs/heads/main"), evidence["main_reflog_sha256"])
        self.protected(record)

    def test_stale_checkpoint_cannot_become_verified_success(self):
        p = self.root / "stale-checkpoint"
        evidence = self.expected[p.name]
        record = copy.deepcopy(evidence["checkpoint"])
        current = git(p, "ls-remote", "origin", "refs/heads/main").stdout.split()[0]
        self.assertNotEqual(current, record["expected_old_oid"])
        self.assertNotEqual(current, record["intended_new_oid"])
        record.update(phase="verified", observed_oid=current)
        self.assertTrue(any("does not match intended" in message for message in checkpoint_errors(record)))
        self.assertEqual(composition.sha(p / ".git/index"), evidence["index_sha256"])
        self.protected(record)

    def test_schema_is_not_proof_of_protected_bytes(self):
        p = self.root / "commit-publish"
        record = self.expected[p.name]["checkpoint"]
        self.assertEqual(checkpoint_errors(record), [])
        (p / "private.txt").write_bytes(b"different\n")
        self.assertNotEqual(composition.sha(p / "private.txt"), record["protected_paths"][str((p / "private.txt").resolve())])

    def test_unknown_and_malformed_records_fail_closed(self):
        record = copy.deepcopy(self.expected["retry-noop"]["checkpoint"])
        record["phase"] = "verified"
        self.assertIn("unknown effects cannot be reported as verified", checkpoint_errors(record))
        for field, value in (("observed_oid", "abc123"), ("phase", []), ("repository", {"worktree": "relative"})):
            invalid = copy.deepcopy(record)
            invalid[field] = value
            self.assertTrue(checkpoint_errors(invalid))

    def test_hex_casing_and_structured_evidence_do_not_weaken_byte_checks(self):
        record = copy.deepcopy(self.expected["retry-noop"]["checkpoint"])
        record["protected_paths"] = {path: digest.upper() for path, digest in record["protected_paths"].items()}
        record["verified_effects"] = [{"kind": "remote", "target": "origin/main",
                                        "value": {"observed_oid": record["observed_oid"], "read_back": True}}]
        self.assertEqual(checkpoint_errors(record), [])
        path = next(iter(record["protected_paths"]))
        self.assertEqual(composition.sha(Path(path)), record["protected_paths"][path].lower())
        record["protected_paths"][path] = "0" * 64
        self.assertNotEqual(composition.sha(Path(path)), record["protected_paths"][path].lower())
        record["verified_effects"][0]["value"] = []
        self.assertTrue(checkpoint_errors(record))

    def test_checkpoint_cli_and_published_schema_shape(self):
        path = self.root / "journal.json"
        journal = copy.deepcopy([self.expected["retry-noop"]["checkpoint"], self.expected["restack-resume"]["checkpoint"]])
        path.write_text(json.dumps(journal), encoding="utf-8")
        schema = json.loads((ROOT / "tests/handoff.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(schema["required"]), set(journal[0]))
        before = composition.sha(self.root / "retry-noop/.git/index")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/skill_contracts.py"), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["valid"])
        self.assertEqual(composition.sha(self.root / "retry-noop/.git/index"), before)
        journal[0]["observed_oid"] = "short"
        path.write_text(json.dumps(journal), encoding="utf-8")
        result = subprocess.run([sys.executable, str(ROOT / "scripts/skill_contracts.py"), str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)["valid"])

    def test_bare_repository_checkpoint_needs_no_invented_worktree(self):
        bare = self.root / "bare.git"
        git(self.root, "init", "--bare", str(bare))
        self.assertEqual(git(bare, "rev-parse", "--is-bare-repository").stdout.strip(), "true")
        record = copy.deepcopy(self.expected["retry-noop"]["checkpoint"])
        record.update(owner="setup-repository", phase="verified", ref=None,
                      expected_old_oid=None, intended_new_oid=None, observed_oid=None,
                      protected_paths={}, protected_refs={}, unknown_effects=[],
                      repository={"worktree": None, "git_dir": str(bare), "common_dir": str(bare)},
                      verified_effects=[{"kind": "repository", "target": str(bare), "value": {"bare": True}}],
                      next_owner=None, next_action="Bare initialization verified; no worktree exists")
        self.assertEqual(checkpoint_errors(record), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
