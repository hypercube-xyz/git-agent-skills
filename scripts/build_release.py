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
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
EXCLUDE_NAMES = {".DS_Store"}
EXCLUDE_PREFIXES = {"dist", ".git"}
VALIDATION = [
    [sys.executable, "scripts/validate_skills.py"],
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


def git(root: Path, *args: str, text: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        check=False,
    )


def require_clean_tracked_state(root: Path = ROOT) -> None:
    checks = [
        ("diff", "--quiet", "--no-ext-diff", "--"),
        ("diff", "--cached", "--quiet", "--no-ext-diff", "HEAD", "--"),
    ]
    for args in checks:
        proc = git(root, *args)
        if proc.returncode == 1:
            raise SystemExit("release build requires committed tracked files")
        if proc.returncode != 0:
            raise SystemExit("unable to inspect tracked release state")


def source_revision(root: Path = ROOT) -> str:
    proc = git(root, "rev-parse", "--verify", "HEAD", text=True)
    if proc.returncode != 0:
        raise SystemExit("unable to resolve release source revision")
    return proc.stdout.strip()


def tracked_files(root: Path = ROOT) -> list[Entry]:
    proc = git(root, "ls-files", "--cached", "--stage", "-z")
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
        if rel.name in EXCLUDE_NAMES:
            continue
        if rel.parts and rel.parts[0] in EXCLUDE_PREFIXES:
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
        digest.update(entry.rel.as_posix().encode() + b"\0")
        digest.update(oct(entry.mode).encode() + b"\0")
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


def archive_time(catalog: dict) -> tuple[int, int, int, int, int, int]:
    released = date.fromisoformat(catalog["release_date"])
    if released.year < 1980:
        raise SystemExit("release date is outside ZIP timestamp range")
    return released.year, released.month, released.day, 0, 0, 0


def release_metadata(entries: list[Entry], catalog: dict) -> dict[str, object]:
    revision = source_revision()
    return {
        "schema_version": 1,
        "package": "git-agent-skills",
        "package_version": catalog["package_version"],
        "release_date": catalog["release_date"],
        "release_tag": f"v{catalog['package_version']}",
        "source_identity": {
            "method": (
                "sha256 over sorted tracked package paths, Git modes, "
                "and file content"
            ),
            "source_tree_sha256": tree_digest(entries),
            "base_revision": catalog.get("base_release", {}),
            "source_revision": {
                "kind": "git-commit",
                "commit": revision,
            },
            "upstream_repository": (
                "https://github.com/hypercube-xyz/git-agent-skills"
            ),
        },
        "compatibility": catalog["compatibility"],
        "contents": {
            "skills": len(catalog["skills"]),
            "tracked_files": len(entries),
        },
    }


def archive_bytes(entries: list[Entry], catalog: dict) -> bytes:
    version = catalog["package_version"]
    prefix = f"git-agent-skills-{version}"
    archive_entries = [
        (entry.rel, entry.mode, entry.path.read_bytes()) for entry in entries
    ]

    names = [rel.as_posix() for rel, _mode, _data in archive_entries]
    if len(names) != len(set(names)):
        raise SystemExit("duplicate archive entries")

    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        "w",
        compression=zipfile.ZIP_STORED,
    ) as archive:
        for rel, mode, data in sorted(
            archive_entries,
            key=lambda item: item[0].as_posix(),
        ):
            info = zipfile.ZipInfo(
                f"{prefix}/{rel.as_posix()}",
                archive_time(catalog),
            )
            info.external_attr = (mode & 0xFFFF) << 16
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, data)

    return buffer.getvalue()


def release_record(
    entries: list[Entry],
    catalog: dict,
    validation_executed: bool,
    reproducibility_checked: bool,
    artifact: dict[str, object],
) -> dict[str, object]:
    record = release_metadata(entries, catalog)
    record["build_environment"] = {
        "python": sys.version.split()[0],
        "git": tool_version(["git", "--version"]),
    }
    record["validation"] = {
        "result": "passed" if validation_executed else "skipped",
        "commands_executed": (
            [" ".join(command) for command in VALIDATION] if validation_executed else []
        ),
        "reproducibility_check": ("passed" if reproducibility_checked else "not-run"),
        "independent_agent_runtime_comparison": (
            "not run unless supplied by an authorized external runner"
        ),
    }
    record["artifact"] = artifact
    return record


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a deterministic release archive from committed tracked files."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Build twice in memory and fail if the archive bytes differ.",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip skill validation and semantic tests before packaging.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the ZIP to this path instead of dist/.",
    )
    args = parser.parse_args()

    catalog = json.loads((ROOT / "skills/catalog.json").read_text(encoding="utf-8"))

    if not args.skip_validation:
        for command in VALIDATION:
            run(command)

    require_clean_tracked_state()
    entries = tracked_files()
    first = archive_bytes(entries, catalog)

    if args.check and first != archive_bytes(entries, catalog):
        raise SystemExit("release archives are not deterministic")

    version = catalog["package_version"]
    output = args.output or DIST / f"git-agent-skills-{version}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(first)

    digest = hashlib.sha256(first).hexdigest()
    checksum = output.with_suffix(output.suffix + ".sha256")
    checksum.write_text(f"{digest}  {output.name}\n", encoding="utf-8")

    artifact = {
        "filename": output.name,
        "sha256": digest,
        "size_bytes": len(first),
    }
    sidecar = release_record(
        entries,
        catalog,
        validation_executed=not args.skip_validation,
        reproducibility_checked=args.check,
        artifact=artifact,
    )
    output.with_suffix(".release.json").write_text(
        json.dumps(sidecar, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(f"PASS: deterministic archive {output}")
    print(f"SHA256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
