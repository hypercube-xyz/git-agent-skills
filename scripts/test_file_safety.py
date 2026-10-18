"""Portable Git trees and disposable installs exercise file-preservation boundaries."""
import json
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stderr, redirect_stdout

import build_release
import link_skills
from smoke_test_git import git, init
from security_git_env import controlled_git_env


class PortableArchivePaths(unittest.TestCase):
    def test_file_directory_case_collision(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"
            init(repo)
            def run(*args, data):
                return subprocess.run(["git", *args], input=data.encode(), cwd=repo,
                                      env=controlled_git_env(), capture_output=True,
                                      check=True).stdout.decode().strip()
            blob = run("hash-object", "-w", "--stdin", data="x\n")
            child = run("mktree", data=f"100644 blob {blob}\tguide.md\n")
            for records in (f"100644 blob {blob}\tDocs\n040000 tree {child}\tdocs\n",
                            f"100644 blob {blob}\tdocs\n040000 tree {child}\tDocs\n",
                            f"100644 blob {blob}\tDocs\n100644 blob {blob}\tdocs\n"):
                with self.subTest(records=records):
                    tree = run("mktree", data=records)
                    with self.assertRaisesRegex(SystemExit, "collision"):
                        build_release.tracked_files(tree, root=repo)
            for records in (f"100644 blob {blob}\tDocs\n040000 tree {child}\tdocumentation\n",
                            f"040000 tree {child}\tDocs\n"):
                with self.subTest(safe_records=records):
                    entries = build_release.tracked_files(run("mktree", data=records), root=repo)
                    self.assertTrue(entries)


class CopyInstallSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "package/skills/example"
        self.source.mkdir(parents=True)
        (self.source / "SKILL.md").write_bytes(b"original\n")
        (self.source / "references").mkdir()
        (self.source / "references/guide.md").write_bytes(b"guide\n")
        catalog = self.source.parent / "catalog.json"
        catalog.write_text(json.dumps({"skills": [{"name": "example", "path": "skills/example"}]}))
        self.target = self.root / "installed"
        self.dest = self.target / "example"

    def run_install(self, *extra):
        with patch.object(link_skills, "__file__", str(self.root / "package/scripts/link_skills.py")), \
             patch.object(sys, "argv", ["link_skills.py", "--target", str(self.target), "--mode", "copy", *extra]), \
             redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as errors:
            result = link_skills.main()
        self.last_error = errors.getvalue()
        return result

    def add_second_skill(self):
        shutil.copytree(self.source, self.source.parent / "other")
        (self.source.parent / "catalog.json").write_text(json.dumps({"skills": [
            {"name": name, "path": f"skills/{name}"} for name in ("example", "other")]}))

    def test_local_add_edit_delete_are_preserved(self):
        self.assertEqual(self.run_install(), 0)
        for action in ("added", "edited", "deleted"):
            with self.subTest(action=action):
                path = self.dest / "references/guide.md"
                if action == "added":
                    path = self.dest / "private.txt"
                    path.write_bytes(b"private\n")
                elif action == "edited":
                    path.write_bytes(b"private edit\n")
                else:
                    path.unlink()
                before = {p.relative_to(self.dest): p.read_bytes() for p in self.dest.rglob("*") if p.is_file()}
                self.assertEqual(self.run_install(), 2)
                self.assertIn(path.name, self.last_error)
                after = {p.relative_to(self.dest): p.read_bytes() for p in self.dest.rglob("*") if p.is_file()}
                self.assertEqual(after, before)
                self.assertEqual(self.run_install("--force-copies"), 0)

    def test_unmodified_install_upgrades_from_original_manifest(self):
        self.assertEqual(self.run_install(), 0)
        (self.source / "SKILL.md").write_bytes(b"upgraded\n")
        self.assertEqual(self.run_install(), 0)
        self.assertEqual((self.dest / "SKILL.md").read_bytes(), b"upgraded\n")

    def test_legacy_and_invalid_manifests_require_force(self):
        self.assertEqual(self.run_install(), 0)
        for value in (None, "not-json", '{"schema_version":999}'):
            with self.subTest(manifest=value):
                manifest = self.dest / link_skills.MANIFEST_NAME
                if value is None:
                    manifest.unlink()
                else:
                    manifest.write_text(value)
                self.assertEqual(self.run_install(), 2)
                self.assertEqual((self.dest / "SKILL.md").read_bytes(), b"original\n")
                self.assertEqual(self.run_install("--force-copies"), 0)

    def test_empty_local_directory_is_preserved(self):
        self.assertEqual(self.run_install(), 0)
        local = self.dest / "personal"
        local.mkdir()
        self.assertEqual(self.run_install(), 2)
        self.assertTrue(local.is_dir())

    def test_all_target_preflight_preserves_earlier_install(self):
        self.add_second_skill()
        self.assertEqual(self.run_install(), 0)
        (self.source / "SKILL.md").write_bytes(b"upgrade\n")
        private = self.target / "other/references/guide.md"
        private.write_bytes(b"private\n")
        self.assertEqual(self.run_install(), 2)
        self.assertEqual((self.dest / "SKILL.md").read_bytes(), b"original\n")
        self.assertEqual(private.read_bytes(), b"private\n")

    def test_nested_edit_after_preflight_rolls_back_prior_install(self):
        self.add_second_skill()
        self.assertEqual(self.run_install(), 0)
        (self.source / "SKILL.md").write_bytes(b"upgrade\n")
        private = self.target / "other/references/guide.md"
        real_install = link_skills.install

        def edit_after_first(source, dest, mode):
            backup = real_install(source, dest, mode)
            private.write_bytes(b"concurrent private edit\n")
            return backup

        with patch.object(link_skills, "install", side_effect=edit_after_first):
            self.assertEqual(self.run_install(), 3)
        self.assertEqual((self.dest / "SKILL.md").read_bytes(), b"original\n")
        self.assertEqual(private.read_bytes(), b"concurrent private edit\n")
        self.assertFalse(list(self.target.glob(".*.backup-*")))
        self.assertFalse(list(self.target.glob(".*.tmp-*")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
