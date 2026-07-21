#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MARKER_NAME = ".git-agent-skills-install-marker"


def reject_nested_symlinks(source: Path) -> None:
    """Reject symlinks, junctions, and unsupported filesystem entries inside *source*.

    This must be called before ``atomic_copy``, which dereferences symlinks
    with ``shutil.copytree(symlinks=False)``.  Without this preflight, a
    checkout containing nested symlinks (e.g.
    ``skills/example/references/private -> ~/.ssh``) could cause copy mode
    to pull files from outside the package root into the installation
    directory.
    """
    for entry in source.rglob("*"):
        try:
            if entry.is_symlink():
                raise SystemExit(
                    f"refusing to copy skill directory containing a symlink: {entry}"
                )
        except OSError:
            # Recurse into protected directories may fail; surface the OS error.
            raise SystemExit(
                f"cannot inspect entry inside skill source {source}: {entry}"
            ) from None


@dataclass(frozen=True)
class Change:
    source: Path
    dest: Path
    previous: str | None  # symlink target when replacing a symlink
    was_copy: bool = False  # True when replacing a copy-installed directory


def current_symlink(dest: Path) -> str | None:
    return os.readlink(dest) if dest.is_symlink() else None


def atomic_symlink(source: Path | str, dest: Path) -> None:
    tmp = dest.parent / f".{dest.name}.tmp-{uuid.uuid4().hex}"
    try:
        tmp.symlink_to(source, target_is_directory=True)
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


def atomic_copy(source: Path, dest: Path) -> None:
    tmp = dest.parent / f".{dest.name}.tmp-{uuid.uuid4().hex}"
    try:
        shutil.copytree(source, tmp, symlinks=False)
        (tmp / MARKER_NAME).write_text("", encoding="utf-8")
        # os.replace cannot atomically replace a non-empty directory on all
        # platforms (macOS returns ENOTEMPTY).  Remove the previous
        # installation first — the preflight and pre-install checks guarantee
        # that *dest* is either absent or a copy-installed directory we own.
        if dest.exists():
            shutil.rmtree(dest)
        tmp.rename(dest)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp, ignore_errors=True)


def can_symlink() -> bool:
    if sys.platform == "win32":
        try:
            import tempfile as _t
            td = Path(_t.mkdtemp())
            (td / "test").symlink_to(td, target_is_directory=True)
            (td / "test").unlink()
            td.rmdir()
            return True
        except OSError:
            return False
    return True


def install(source: Path, dest: Path, mode: str) -> None:
    if mode == "symlink":
        atomic_symlink(source, dest)
    elif mode == "copy":
        atomic_copy(source, dest)
    else:  # auto
        if can_symlink():
            atomic_symlink(source, dest)
        else:
            atomic_copy(source, dest)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    skills_path = root / "skills"
    if skills_path.is_symlink():
        raise SystemExit("refusing a symlinked skills package root")
    skills_root = skills_path.resolve(strict=True)
    catalog_path = skills_root / "catalog.json"
    if catalog_path.is_symlink():
        raise SystemExit("refusing a symlinked skills catalog")
    parser = argparse.ArgumentParser(description="Link packaged skills after an all-target preflight.")
    parser.add_argument(
        "--target",
        type=Path,
        default=Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude")) / "skills",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-symlinks", action="store_true", help="Replace foreign symlinks, never files/directories.")
    parser.add_argument("--force-copies", action="store_true",
                        help="Replace copy-installed skill directories even without the install marker.")
    parser.add_argument("--mode", choices=["auto", "symlink", "copy"], default="auto",
                        help="Installation mode: auto (symlink or copy fallback), symlink, copy.")
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
    # Check raw path for symlink before resolving — .resolve() follows symlinks.
    if target_input.is_symlink():
        errors.append(f"target must be a real directory, not a symlink: {target_input}")
    target = target_input.resolve(strict=False)
    if target.exists() and not target.is_dir():
        errors.append(f"target must resolve to a real directory: {target_input}")

    # Determine the effective installation mode for preflight decisions.
    effective_mode = args.mode
    if effective_mode == "auto":
        effective_mode = "symlink" if can_symlink() else "copy"

    plan: list[Change] = []
    for name in names:
        candidate = skills_root / name
        if candidate.is_symlink():
            errors.append(f"skill source is a symlink: {name}")
            continue
        source = candidate.resolve(strict=True)
        if source.parent != skills_root or source.name != name or not source.is_dir():
            errors.append(f"skill source escapes package root: {name}")
            continue
        if effective_mode == "copy":
            # Reject nested symlinks inside the source before copy dereferences them.
            reject_nested_symlinks(source)
        dest = target / name
        if dest.parent != target:
            errors.append(f"destination escapes target: {dest}")
            continue
        if dest.is_symlink():
            current = os.readlink(dest)
            resolved = (dest.parent / current).resolve(strict=False)
            if resolved == source:
                continue
            if not args.force_symlinks:
                errors.append(f"foreign symlink: {dest} -> {current}")
            else:
                plan.append(Change(source, dest, current))
        elif dest.is_dir() and (dest / MARKER_NAME).exists():
            # Copy-installed directory from a previous run — safe to replace.
            plan.append(Change(source, dest, None, was_copy=True))
        elif dest.is_dir() and args.force_copies:
            plan.append(Change(source, dest, None, was_copy=True))
        elif dest.is_dir():
            errors.append(
                f"refusing to replace non-symlink directory without install marker: {dest}"
                f" (use --force-copies to override)"
            )
        elif dest.is_file():
            errors.append(f"refusing to replace non-symlink file: {dest}")
        else:
            plan.append(Change(source, dest, None))

    if errors:
        print("preflight failed; no changes made:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    action = "LINK" if args.mode != "copy" else "COPY"
    print(f"target: {target} (from {target_input})")
    for change in plan:
        print(f"{'WOULD ' + action if args.dry_run else action} {change.dest} -> {change.source}")
    if args.dry_run:
        return 0

    target.mkdir(parents=True, exist_ok=True)
    touched: list[Change] = []
    try:
        for change in plan:
            if change.was_copy:
                if not change.dest.is_dir() or not (change.dest / MARKER_NAME).exists():
                    raise OSError(f"copy destination changed after preflight: {change.dest}")
            elif change.previous is None:
                if change.dest.exists():
                    raise OSError(f"destination changed after preflight: {change.dest}")
            else:
                observed = current_symlink(change.dest)
                if observed != change.previous:
                    raise OSError(f"symlink changed after preflight: {change.dest}")
            install(change.source, change.dest, args.mode)
            touched.append(change)
    except Exception as exc:
        rollback_errors: list[str] = []
        for change in reversed(touched):
            try:
                if change.dest.is_symlink():
                    if change.previous is None:
                        change.dest.unlink()
                    else:
                        atomic_symlink(change.previous, change.dest)
                elif change.dest.is_dir():
                    shutil.rmtree(change.dest)
            except OSError as rollback_exc:
                rollback_errors.append(f"{change.dest}: {rollback_exc}")
        if rollback_errors:
            print(f"install failed and rollback was incomplete: {exc}", file=sys.stderr)
            for error in rollback_errors:
                print(f"- {error}", file=sys.stderr)
        else:
            print(f"install failed; invocation changes were rolled back: {exc}", file=sys.stderr)
        return 3

    print(f"installed {len(plan)} skills; {len(names) - len(plan)} already correct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
