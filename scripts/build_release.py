#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import stat
import sys
import tempfile
import unicodedata
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath

from security_git_env import controlled_git_env, resolve_git

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
EXCLUDE_NAMES = {".DS_Store"}
EXCLUDE_PREFIXES = {"dist", ".git"}
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
WINDOWS_INVALID = set('<>:"|?*')
VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]*$")


@dataclass(frozen=True)
class Entry:
    rel: PurePosixPath
    mode: int
    data: bytes


def git(*args: str, text: bool = False, check: bool = False, root: Path = ROOT) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        [resolve_git(), "-C", str(root), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=text,
        check=False,
        env=controlled_git_env(),
    )
    if check and proc.returncode:
        message = proc.stderr if text else proc.stderr.decode(errors="replace")
        raise SystemExit(message.strip() or f"git {' '.join(args)} failed")
    return proc


def source_revision(root: Path = ROOT) -> str:
    return git("rev-parse", "--verify", "HEAD", text=True, check=True, root=root).stdout.strip()


def source_tree_oid(revision: str, root: Path = ROOT) -> str:
    return git("rev-parse", "--verify", f"{revision}^{{tree}}", text=True, check=True, root=root).stdout.strip()


def validate_path(raw: bytes) -> PurePosixPath:
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"release path is not valid UTF-8: {raw!r}") from exc
    if not text or text.startswith("/") or "\\" in text:
        raise SystemExit(f"unsafe release path: {text!r}")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in text):
        raise SystemExit(f"control character in release path: {text!r}")
    raw_parts = text.split("/")
    if any(part in {"", ".", ".."} for part in raw_parts):
        raise SystemExit(f"non-canonical release path: {text!r}")
    path = PurePosixPath(*raw_parts)
    for part in path.parts:
        normalized = unicodedata.normalize("NFC", part)
        if normalized != part:
            raise SystemExit(f"non-NFC release path: {text!r}")
        if part.endswith((".", " ")) or any(ch in WINDOWS_INVALID for ch in part):
            raise SystemExit(f"non-portable release path: {text!r}")
        if part.split(".", 1)[0].upper() in WINDOWS_RESERVED:
            raise SystemExit(f"reserved release path: {text!r}")
    return path


def tracked_files(revision: str, root: Path = ROOT) -> list[Entry]:
    proc = git("ls-tree", "-r", "-z", "--full-tree", revision, root=root)
    if proc.returncode:
        raise SystemExit("unable to enumerate committed release files")

    entries: list[Entry] = []
    collision_keys: dict[str, PurePosixPath] = {}
    for record in proc.stdout.split(b"\0"):
        if not record:
            continue
        try:
            header, raw_path = record.split(b"\t", 1)
            raw_mode, raw_type, raw_oid = header.split(b" ", 2)
        except ValueError as exc:
            raise SystemExit("unexpected git ls-tree output") from exc

        rel = validate_path(raw_path)
        if rel.name in EXCLUDE_NAMES or (rel.parts and rel.parts[0] in EXCLUDE_PREFIXES):
            continue

        mode = int(raw_mode, 8)
        if raw_type != b"blob" or mode not in {0o100644, 0o100755}:
            raise SystemExit(f"unsupported committed entry {raw_mode.decode()} {raw_type.decode()}: {rel}")

        key = unicodedata.normalize("NFC", rel.as_posix()).casefold()
        previous = collision_keys.setdefault(key, rel)
        if previous != rel:
            raise SystemExit(f"portable path collision: {previous} and {rel}")

        oid = raw_oid.decode("ascii")
        blob = git("cat-file", "blob", oid, check=True, root=root).stdout
        entries.append(Entry(rel=rel, mode=mode, data=blob))

    return sorted(entries, key=lambda entry: entry.rel.as_posix())


def tree_digest(entries: list[Entry]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        digest.update(entry.rel.as_posix().encode("utf-8") + b"\0")
        digest.update(oct(entry.mode).encode("ascii") + b"\0")
        digest.update(hashlib.sha256(entry.data).digest())
    return digest.hexdigest()


def tool_version(cmd: list[str]) -> str:
    try:
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True,
            env=controlled_git_env(),
        ).stdout.strip()
    except Exception:
        return "unavailable"


def archive_time(catalog: dict) -> tuple[int, int, int, int, int, int]:
    released = date.fromisoformat(catalog["release_date"])
    if released.year < 1980:
        raise SystemExit("release date is outside ZIP timestamp range")
    return released.year, released.month, released.day, 0, 0, 0


def catalog_from_entries(entries: list[Entry]) -> dict:
    for entry in entries:
        if entry.rel.as_posix() == "skills/catalog.json":
            catalog = json.loads(entry.data.decode("utf-8"))
            version = str(catalog.get("package_version", ""))
            if not VERSION_RE.fullmatch(version):
                raise SystemExit(f"unsafe package version: {version!r}")
            return catalog
    raise SystemExit("committed release input lacks skills/catalog.json")


def release_metadata(entries: list[Entry], catalog: dict, revision: str, root: Path = ROOT) -> dict[str, object]:
    return {
        "schema_version": 2,
        "package": "git-agent-skills",
        "package_version": catalog["package_version"],
        "release_date": catalog["release_date"],
        "release_tag": f"v{catalog['package_version']}",
        "source_identity": {
            "method": "sha256 over sorted committed paths, Git modes, and immutable blob content",
            "source_tree_sha256": tree_digest(entries),
            "git_tree_oid": source_tree_oid(revision, root=root),
            "base_revision": catalog.get("base_release", {}),
            "source_revision": {"kind": "git-commit", "commit": revision},
            "upstream_repository": "https://github.com/hypercube-xyz/git-agent-skills",
        },
        "compatibility": catalog["compatibility"],
        "contents": {"skills": len(catalog["skills"]), "tracked_files": len(entries)},
    }


def archive_bytes(entries: list[Entry], catalog: dict) -> bytes:
    prefix = f"git-agent-skills-{catalog['package_version']}"
    names = [entry.rel.as_posix() for entry in entries]
    if len(names) != len(set(names)):
        raise SystemExit("duplicate archive entries")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as archive:
        for entry in entries:
            info = zipfile.ZipInfo(f"{prefix}/{entry.rel.as_posix()}", archive_time(catalog))
            info.external_attr = (entry.mode & 0xFFFF) << 16
            info.create_system = 3
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, entry.data)
    return buffer.getvalue()


def atomic_write(path: Path, data: bytes, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def release_path(output: Path) -> Path:
    return output.with_suffix(".release.json")


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


_TRUSTED_SYMLINKS: dict[Path, Path] = {}
if sys.platform == "darwin":
    _TRUSTED_SYMLINKS = {
        Path("/tmp"): Path("/private/tmp"),
        Path("/var"): Path("/private/var"),
    }


def reject_symlink_components(path: Path) -> None:
    # Walk raw abspath components; reject symlinks except known macOS root aliases.
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    parts = absolute.parts[1:] if absolute.anchor else absolute.parts
    for part in parts:
        current /= part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            break
        if stat.S_ISLNK(mode):
            trusted_target = _TRUSTED_SYMLINKS.get(current)
            if trusted_target is None:
                raise SystemExit(f"release output contains a symlink component: {current}")
            resolved = current.resolve(strict=False)
            if resolved != trusted_target:
                raise SystemExit(f"trusted symlink {current} points to {resolved}, expected {trusted_target}")


def validate_output_paths(output: Path, entries: list[Entry], root: Path = ROOT) -> tuple[Path, Path, Path]:
    raw_output = output.expanduser()
    reject_symlink_components(raw_output)
    output = raw_output.resolve(strict=False)
    root = root.resolve(strict=True)
    dist = (root / "dist").resolve(strict=False)
    if is_within(output, root) and not is_within(output, dist):
        raise SystemExit("release output inside the repository must be under dist/")
    if output == dist or output.name in {"", ".", ".."}:
        raise SystemExit("release output must name a file")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in output.name):
        raise SystemExit("release output filename contains a control character")
    checksum = output.with_suffix(output.suffix + ".sha256")
    metadata = release_path(output)
    if len({output, checksum, metadata}) != 3:
        raise SystemExit("release output and sidecar paths must be distinct")
    tracked = {(root / Path(*entry.rel.parts)).resolve(strict=False) for entry in entries}
    for path in (output, checksum, metadata):
        if path in tracked:
            raise SystemExit(f"release output aliases a tracked source file: {path}")
        if path.exists() and path.is_dir():
            raise SystemExit(f"release output path is a directory: {path}")
    return output, checksum, metadata


def release_record(
    entries: list[Entry],
    catalog: dict,
    revision: str,
    reproducibility_checked: bool,
    artifact: dict[str, object],
    root: Path = ROOT,
) -> dict[str, object]:
    record = release_metadata(entries, catalog, revision, root=root)
    record["build_environment"] = {
        "python": sys.version.split()[0],
        "git": tool_version([resolve_git(), "--version"]),
    }
    record["validation"] = {
        "result": "not run by builder; CI validates before invoking builder",
        "reproducibility_check": "passed" if reproducibility_checked else "not-run",
        "reproducibility_note": "in-process deterministic serialization check; cross-environment reproducibility requires comparing digests from independent jobs",
    }
    record["artifact"] = artifact
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a deterministic release archive from immutable committed blobs.")
    parser.add_argument("--check", action="store_true", help="Build twice in memory and fail if bytes differ.")
    parser.add_argument("--output", type=Path, help="Write ZIP here instead of dist/.")
    args = parser.parse_args()

    revision = source_revision()
    entries = tracked_files(revision)
    catalog = catalog_from_entries(entries)
    first = archive_bytes(entries, catalog)
    if args.check and first != archive_bytes(entries, catalog):
        raise SystemExit("release archives are not deterministic")

    version = catalog["package_version"]
    output, checksum, metadata_path = validate_output_paths(
        args.output or DIST / f"git-agent-skills-{version}.zip", entries
    )
    digest = hashlib.sha256(first).hexdigest()
    artifact = {"filename": output.name, "sha256": digest, "size_bytes": len(first)}
    metadata = release_record(
        entries,
        catalog,
        revision,
        reproducibility_checked=args.check,
        artifact=artifact,
    )

    atomic_write(output, first)
    atomic_write(checksum, f"{digest}  {output.name}\n".encode())
    atomic_write(metadata_path, (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode())

    print(f"PASS: deterministic archive {output}")
    print(f"SHA256: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
