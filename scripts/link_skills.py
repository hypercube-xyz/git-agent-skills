#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKER_NAME = ".git-agent-skills-install-marker"
MARKER_CONTENT = "git-agent-skills-copy-v1\n"
_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def path_present(path: Path) -> bool:
    """Return True for regular paths and broken symlinks."""
    return path.exists() or path.is_symlink()


def is_reparse_point(path: Path) -> bool:
    """Return True for Windows junctions and other reparse-point entries."""
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & _REPARSE_POINT)


def marker_valid(directory: Path) -> bool:
    marker = directory / MARKER_NAME
    try:
        return (
            marker.is_file()
            and not marker.is_symlink()
            and not is_reparse_point(marker)
            and marker.read_text(encoding="utf-8") == MARKER_CONTENT
        )
    except OSError:
        return False


def directory_identity(directory: Path) -> tuple[int, int, int, int]:
    st = directory.stat(follow_symlinks=False)
    return (st.st_dev, st.st_ino, st.st_mtime_ns, st.st_size)


def reject_nested_symlinks(source: Path) -> None:
    """Reject links, reparse points, and non-file entries below *source*.

    Copy mode must never dereference repository-controlled filesystem objects.
    Walk with ``os.scandir`` and ``follow_symlinks=False`` so inspection itself
    does not traverse a link or Windows junction.
    """
    pending = [source]
    while pending:
        directory = pending.pop()
        try:
            with os.scandir(directory) as entries:
                for raw in entries:
                    entry = Path(raw.path)
                    try:
                        if raw.is_symlink() or is_reparse_point(entry):
                            raise SystemExit(
                                "refusing to copy skill directory containing a link "
                                f"or reparse point: {entry}"
                            )
                        if raw.is_dir(follow_symlinks=False):
                            pending.append(entry)
                        elif not raw.is_file(follow_symlinks=False):
                            raise SystemExit(
                                "refusing to copy skill directory containing an "
                                f"unsupported filesystem entry: {entry}"
                            )
                    except OSError as exc:
                        raise SystemExit(
                            f"cannot inspect entry inside skill source {source}: "
                            f"{entry}: {exc}"
                        ) from None
        except OSError as exc:
            raise SystemExit(
                f"cannot inspect skill source directory {directory}: {exc}"
            ) from None


@dataclass(frozen=True)
class Change:
    source: Path
    dest: Path
    previous_kind: str
    previous_link: str | None = None
    previous_identity: tuple[int, int, int, int] | None = None


@dataclass(frozen=True)
class AppliedChange:
    change: Change
    backup: Path | None


def current_symlink(dest: Path) -> str | None:
    return os.readlink(dest) if dest.is_symlink() else None


def remove_path(path: Path) -> None:
    if not path_present(path):
        return
    if path.is_symlink():
        path.unlink()
    elif getattr(path, "is_junction", lambda: False)():
        path.rmdir()
    elif path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def promote_staged(staged: Path, dest: Path) -> Path | None:
    """Promote *staged* and preserve any previous destination for rollback."""
    backup = None
    if path_present(dest):
        backup = dest.parent / f".{dest.name}.backup-{uuid.uuid4().hex}"
        dest.rename(backup)
    try:
        staged.rename(dest)
    except Exception:
        if backup is not None and path_present(backup) and not path_present(dest):
            backup.rename(dest)
        raise
    return backup


def atomic_symlink(source: Path | str, dest: Path) -> Path | None:
    tmp = dest.parent / f".{dest.name}.tmp-{uuid.uuid4().hex}"
    try:
        tmp.symlink_to(source, target_is_directory=True)
        return promote_staged(tmp, dest)
    finally:
        if path_present(tmp):
            remove_path(tmp)


def atomic_copy(source: Path, dest: Path) -> Path | None:
    tmp = dest.parent / f".{dest.name}.tmp-{uuid.uuid4().hex}"
    try:
        shutil.copytree(source, tmp, symlinks=False)
        (tmp / MARKER_NAME).write_text(MARKER_CONTENT, encoding="utf-8")
        return promote_staged(tmp, dest)
    finally:
        if path_present(tmp):
            remove_path(tmp)


def can_symlink() -> bool:
    if sys.platform == "win32":
        import tempfile as _t

        td = Path(_t.mkdtemp())
        try:
            (td / "test").symlink_to(td, target_is_directory=True)
            (td / "test").unlink()
            return True
        except OSError:
            return False
        finally:
            shutil.rmtree(td, ignore_errors=True)
    return True


def install(source: Path, dest: Path, mode: str) -> Path | None:
    if mode == "symlink":
        return atomic_symlink(source, dest)
    if mode == "copy":
        return atomic_copy(source, dest)
    raise ValueError(f"unresolved installation mode: {mode}")


def verify_previous_state(change: Change) -> None:
    if change.previous_kind == "absent":
        if path_present(change.dest):
            raise OSError(f"destination changed after preflight: {change.dest}")
        return

    if change.previous_kind == "symlink":
        if current_symlink(change.dest) != change.previous_link:
            raise OSError(f"symlink changed after preflight: {change.dest}")
        return

    if (
        not change.dest.is_dir()
        or change.dest.is_symlink()
        or is_reparse_point(change.dest)
        or directory_identity(change.dest) != change.previous_identity
    ):
        raise OSError(f"copy destination changed after preflight: {change.dest}")

    if change.previous_kind == "marked-copy" and not marker_valid(change.dest):
        raise OSError(f"copy install marker changed after preflight: {change.dest}")


def rollback(applied: list[AppliedChange]) -> list[str]:
    errors: list[str] = []
    for item in reversed(applied):
        try:
            remove_path(item.change.dest)
            if item.backup is not None and path_present(item.backup):
                item.backup.rename(item.change.dest)
        except OSError as exc:
            errors.append(f"{item.change.dest}: {exc}")
    return errors


def cleanup_backups(applied: list[AppliedChange]) -> list[str]:
    errors: list[str] = []
    for item in applied:
        if item.backup is None:
            continue
        try:
            remove_path(item.backup)
        except OSError as exc:
            errors.append(f"{item.backup}: {exc}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    skills_path = root / "skills"
    if skills_path.is_symlink() or is_reparse_point(skills_path):
        raise SystemExit("refusing a linked or reparse-point skills package root")
    skills_root = skills_path.resolve(strict=True)
    catalog_path = skills_root / "catalog.json"
    if catalog_path.is_symlink() or is_reparse_point(catalog_path):
        raise SystemExit("refusing a linked or reparse-point skills catalog")

    parser = argparse.ArgumentParser(
        description="Install packaged skills after an all-target preflight."
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
        / "skills",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--force-symlinks",
        action="store_true",
        help="Replace foreign symlinks, never regular files or reparse points.",
    )
    parser.add_argument(
        "--force-copies",
        action="store_true",
        help="Replace an existing real directory that lacks a valid install marker.",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "symlink", "copy"],
        default="auto",
        help="Installation mode: auto (symlink or copy fallback), symlink, copy.",
    )
    args = parser.parse_args()

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    rows = catalog.get("skills", [])
    names: list[str] = []
    errors: list[str] = []
    for item in rows:
        name = item.get("name", "")
        if not NAME_RE.fullmatch(name):
            errors.append(f"invalid skill name: {name!r}")
            continue
        if item.get("path") != f"skills/{name}":
            errors.append(f"noncanonical catalog path for {name}")
            continue
        names.append(name)
    if len(names) != len(set(names)):
        errors.append("duplicate skill names")

    target_input = args.target.expanduser()
    if target_input.is_symlink() or is_reparse_point(target_input):
        errors.append(
            f"target must be a real directory, not a link or reparse point: "
            f"{target_input}"
        )
    target = target_input.resolve(strict=False)
    if target.exists() and not target.is_dir():
        errors.append(f"target must resolve to a real directory: {target_input}")

    effective_mode = args.mode
    if effective_mode == "auto":
        effective_mode = "symlink" if can_symlink() else "copy"

    plan: list[Change] = []
    for name in names:
        candidate = skills_root / name
        if candidate.is_symlink() or is_reparse_point(candidate):
            errors.append(f"skill source is a link or reparse point: {name}")
            continue
        source = candidate.resolve(strict=True)
        if source.parent != skills_root or source.name != name or not source.is_dir():
            errors.append(f"skill source escapes package root: {name}")
            continue
        if effective_mode == "copy":
            reject_nested_symlinks(source)

        dest = target / name
        if dest.parent != target:
            errors.append(f"destination escapes target: {dest}")
            continue

        if dest.is_symlink():
            current = os.readlink(dest)
            resolved = (dest.parent / current).resolve(strict=False)
            if effective_mode == "symlink" and resolved == source:
                continue
            if resolved != source and not args.force_symlinks:
                errors.append(f"foreign symlink: {dest} -> {current}")
            else:
                plan.append(Change(source, dest, "symlink", previous_link=current))
        elif is_reparse_point(dest):
            errors.append(f"refusing to replace destination reparse point: {dest}")
        elif dest.is_dir():
            identity = directory_identity(dest)
            if marker_valid(dest):
                plan.append(
                    Change(source, dest, "marked-copy", previous_identity=identity)
                )
            elif args.force_copies:
                plan.append(
                    Change(source, dest, "forced-directory", previous_identity=identity)
                )
            else:
                errors.append(
                    "refusing to replace directory without a valid install marker: "
                    f"{dest} (use --force-copies to override)"
                )
        elif dest.exists():
            errors.append(f"refusing to replace non-directory destination: {dest}")
        else:
            plan.append(Change(source, dest, "absent"))

    if errors:
        print("preflight failed; no changes made:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    action = "LINK" if effective_mode == "symlink" else "COPY"
    print(f"target: {target} (from {target_input})")
    for change in plan:
        prefix = "WOULD " if args.dry_run else ""
        print(f"{prefix}{action} {change.dest} -> {change.source}")
    if args.dry_run:
        return 0

    target.mkdir(parents=True, exist_ok=True)
    applied: list[AppliedChange] = []
    try:
        for change in plan:
            verify_previous_state(change)
            backup = install(change.source, change.dest, effective_mode)
            applied.append(AppliedChange(change, backup))
    except Exception as exc:
        rollback_errors = rollback(applied)
        if rollback_errors:
            print(f"install failed and rollback was incomplete: {exc}", file=sys.stderr)
            for error in rollback_errors:
                print(f"- {error}", file=sys.stderr)
        else:
            print(
                f"install failed; invocation changes were rolled back: {exc}",
                file=sys.stderr,
            )
        return 3

    cleanup_errors = cleanup_backups(applied)
    if cleanup_errors:
        print("install succeeded but backup cleanup was incomplete:", file=sys.stderr)
        for error in cleanup_errors:
            print(f"- {error}", file=sys.stderr)
        return 3

    print(f"installed {len(plan)} skills; {len(names) - len(plan)} already correct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
