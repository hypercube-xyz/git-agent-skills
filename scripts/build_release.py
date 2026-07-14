#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
FIXED_TIME = (2026, 7, 15, 0, 0, 0)
EXCLUDE_NAMES = {".DS_Store", "RELEASE-MANIFEST.json"}
EXCLUDE_PREFIXES = {"dist"}
VALIDATION = [
    [sys.executable, "scripts/validate_skills.py"],
    [sys.executable, "scripts/evaluate_fixtures.py"],
    [sys.executable, "scripts/smoke_test_git.py"],
]


@dataclass(frozen=True)
class Entry:
    rel: Path
    path: Path
    mode: int


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode:
        raise SystemExit(proc.returncode)


def require_clean_tracked_state(root: Path = ROOT) -> None:
    """Reject staged or unstaged changes to tracked release inputs."""
    checks = [
        ["diff", "--quiet", "--no-ext-diff", "--"],
        ["diff", "--cached", "--quiet", "--no-ext-diff", "HEAD", "--"],
    ]
    for args in checks:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if proc.returncode == 1:
            raise SystemExit("release build requires committed tracked files")
        if proc.returncode != 0:
            raise SystemExit("unable to inspect tracked release state")


def source_revision(root: Path = ROOT) -> str:
    proc = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit("unable to resolve release source revision")
    return proc.stdout.strip()


def tracked_files(root: Path = ROOT) -> list[Entry]:
    """Return tracked regular files with executable modes from the Git index.

    Untracked and ignored files are not release inputs. Tracked symlinks and other
    non-regular modes are rejected instead of being dereferenced into the archive.
    """
    proc = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--cached", "--stage", "-z"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode:
        raise SystemExit("unable to enumerate tracked release files")

    entries: list[Entry] = []
    for record in proc.stdout.split(b"\0"):
        if not record:
            continue
        try:
            header, raw_path = record.split(b"\t", 1)
            raw_mode, _oid, raw_stage = header.split(b" ", 2)
        except ValueError as exc:
            raise SystemExit("unexpected git ls-files output") from exc
        if raw_stage != b"0":
            raise SystemExit("release input contains an unmerged index entry")

        rel = Path(os.fsdecode(raw_path))
        if rel.name in EXCLUDE_NAMES or (rel.parts and rel.parts[0] in EXCLUDE_PREFIXES):
            continue

        mode = int(raw_mode, 8)
        if mode == 0o120000:
            raise SystemExit(f"release input contains a tracked symlink: {rel}")
        if mode not in {0o100644, 0o100755}:
            raise SystemExit(f"unsupported tracked mode {raw_mode.decode()}: {rel}")

        path = root / rel
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"tracked release file is missing or not regular: {rel}")
        entries.append(Entry(rel=rel, path=path, mode=mode))

    return sorted(entries, key=lambda entry: entry.rel.as_posix())


def tree_digest(entries: list[Entry]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        digest.update(entry.rel.as_posix().encode("utf-8") + b"\0")
        digest.update(oct(entry.mode).encode("ascii") + b"\0")
        digest.update(hashlib.sha256(entry.path.read_bytes()).digest())
    return digest.hexdigest()


def tool_version(cmd: list[str]) -> str:
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
        ).stdout.strip()
    except Exception:
        return "unavailable"


def package_manifest(entries: list[Entry], version: str) -> dict[str, object]:
    """Return source-derived metadata embedded in the deterministic archive."""
    return {
        "schema_version": 1,
        "package": "git-agent-skills",
        "package_version": version,
        "release_date": "2026-07-15",
        "source_identity": {
            "method": "sha256 over sorted tracked package paths, Git modes, and file content",
            "source_tree_sha256": tree_digest(entries),
            "upstream_repository": "https://github.com/hypercube-xyz/git-agent-skills",
        },
        "compatibility": {
            "python_minimum": "3.9",
            "git_minimum": "2.35",
            "ci_os": "Ubuntu",
            "tested_packaging_clients": ["Skills CLI 1.5.17", "Claude Code 2.1.209"],
        },
    }


def archive_bytes(entries: list[Entry], version: str) -> bytes:
    prefix = f"git-agent-skills-{version}"
    embedded = json.dumps(
        package_manifest(entries, version), indent=2, sort_keys=True
    ).encode("utf-8") + b"\n"

    all_entries = [(Path("RELEASE-MANIFEST.json"), 0o100644, embedded)] + [
        (entry.rel, entry.mode, entry.path.read_bytes()) for entry in entries
    ]
    names = [rel.as_posix() for rel, _mode, _data in all_entries]
    if len(names) != len(set(names)):
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise SystemExit(f"duplicate archive entries: {duplicates}")
    if names.count("RELEASE-MANIFEST.json") != 1:
        raise SystemExit("release archive must contain exactly one RELEASE-MANIFEST.json")

    buffer = io.BytesIO()
    # ZIP_STORED avoids zlib-version-dependent compressed output.
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for rel, mode, data in sorted(all_entries, key=lambda item: item[0].as_posix()):
            info = zipfile.ZipInfo(f"{prefix}/{rel.as_posix()}", FIXED_TIME)
            info.external_attr = (mode & 0xFFFF) << 16
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, data)
    return buffer.getvalue()


def release_record(
    entries: list[Entry],
    version: str,
    validation_executed: bool,
    reproducibility_checked: bool,
    artifact: dict[str, object],
) -> dict[str, object]:
    record = package_manifest(entries, version)
    record["source_revision"] = {"commit": source_revision()}
    record["build_environment"] = {
        "python": sys.version.split()[0],
        "git": tool_version(["git", "--version"]),
    }
    record["validation"] = {
        "result": "passed" if validation_executed else "skipped",
        "commands_executed": (
            [
                "python3 scripts/validate_skills.py",
                "python3 scripts/evaluate_fixtures.py",
                "python3 scripts/smoke_test_git.py",
            ]
            if validation_executed
            else []
        ),
        "reproducibility_check": "passed" if reproducibility_checked else "not-run",
        "agent_runtime_cases": "not run",
    }
    record["artifact"] = artifact
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--skip-validation", action="store_true")
    args = parser.parse_args()

    catalog = json.loads((ROOT / "skills/catalog.json").read_text(encoding="utf-8"))
    version = catalog["package_version"]

    if not args.skip_validation:
        for cmd in VALIDATION:
            run(cmd)
    validation_executed = not args.skip_validation

    require_clean_tracked_state()
    entries = tracked_files()
    first = archive_bytes(entries, version)
    if args.check:
        second = archive_bytes(entries, version)
        if first != second:
            raise SystemExit("release archives are not deterministic")

    DIST.mkdir(exist_ok=True)
    name = f"git-agent-skills-{version}.zip"
    output = DIST / name
    output.write_bytes(first)
    digest = hashlib.sha256(first).hexdigest()
    (DIST / f"{name}.sha256").write_text(f"{digest}  {name}\n", encoding="utf-8")

    artifact = {"filename": name, "sha256": digest, "size_bytes": len(first)}
    sidecar = release_record(entries, version, validation_executed, args.check, artifact)
    (DIST / f"git-agent-skills-{version}.release.json").write_text(
        json.dumps(sidecar, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    print(f"PASS: deterministic archive {output}")
    print(f"SHA256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
