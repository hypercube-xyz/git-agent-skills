"""Release identity must be rejected before serialization or filesystem writes."""
import json
import sys
import unittest
from pathlib import PurePosixPath
from unittest.mock import patch

import build_release as release


def inputs(version="2.0.1", plugin="2.0.1"):
    catalog = {"package_version": version, "release_date": "2026-10-18",
               "compatibility": {}, "skills": []}
    entries = [release.Entry(PurePosixPath("skills/catalog.json"), 0o100644,
                             json.dumps(catalog).encode())]
    if plugin is not None:
        entries.append(release.Entry(PurePosixPath(".claude-plugin/plugin.json"),
                                     0o100644, json.dumps({"version": plugin}).encode()))
    return entries, catalog


class ReleaseVersions(unittest.TestCase):
    def test_tag_plugin_catalog_and_metadata_agree(self):
        entries, catalog = inputs()
        release.validate_release_versions(entries, catalog, "v2.0.1")
        with patch.object(release, "source_tree_oid", return_value="tree"):
            metadata = release.release_metadata(entries, catalog, "commit")
        self.assertEqual(metadata["release_tag"], "v2.0.1")
        self.assertEqual(metadata["package_version"], "2.0.1")

    def test_mismatch_stops_before_build(self):
        for tag, plugin in (("v2.0.2", "2.0.1"), ("2.0.1", "2.0.1"),
                            ("v2.0.1", "2.0.0"), ("v2.0.1", None)):
            with self.subTest(tag=tag, plugin=plugin):
                entries, _ = inputs(plugin=plugin)
                with patch.object(sys, "argv", ["build_release.py", "--release-tag", tag]), \
                     patch.object(release, "source_revision", return_value="commit"), \
                     patch.object(release, "tracked_files", return_value=entries), \
                     patch.object(release, "archive_bytes") as build, \
                     patch.object(release, "atomic_write") as write:
                    with self.assertRaisesRegex(SystemExit, "mismatch|lacks"):
                        release.main()
                    build.assert_not_called()
                    write.assert_not_called()

    def test_validation_only_never_builds_or_writes(self):
        entries, _ = inputs()
        with patch.object(sys, "argv", ["build_release.py", "--release-tag", "v2.0.1", "--validate-only"]), \
             patch.object(release, "source_revision", return_value="commit"), \
             patch.object(release, "tracked_files", return_value=entries), \
             patch.object(release, "archive_bytes") as build, \
             patch.object(release, "atomic_write") as write:
            self.assertEqual(release.main(), 0)
            build.assert_not_called()
            write.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
