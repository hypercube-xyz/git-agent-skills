#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Change:
    source: Path
    dest: Path
    previous: str | None


def current_symlink(dest: Path) -> str | None:
    return os.readlink(dest) if dest.is_symlink() else None


def atomic_symlink(source: Path | str, dest: Path) -> None:
    tmp = dest.parent / f".{dest.name}.tmp-{uuid.uuid4().hex}"
    try:
        tmp.symlink_to(source, target_is_directory=True)
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)


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
    target = target_input.resolve(strict=False)
    if target.exists() and (target.is_symlink() or not target.is_dir()):
        errors.append(f"target must resolve to a real directory: {target_input}")

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
        elif dest.exists():
            errors.append(f"refusing to replace non-symlink: {dest}")
        else:
            plan.append(Change(source, dest, None))

    if errors:
        print("preflight failed; no changes made:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2

    print(f"target: {target} (from {target_input})")
    for change in plan:
        print(f"{'WOULD LINK' if args.dry_run else 'LINK'} {change.dest} -> {change.source}")
    if args.dry_run:
        return 0

    target.mkdir(parents=True, exist_ok=True)
    touched: list[Change] = []
    try:
        for change in plan:
            observed = current_symlink(change.dest)
            if change.previous is None:
                if observed is not None or change.dest.exists():
                    raise OSError(f"destination changed after preflight: {change.dest}")
            elif observed != change.previous:
                raise OSError(f"symlink changed after preflight: {change.dest}")
            atomic_symlink(change.source, change.dest)
            touched.append(change)
    except Exception as exc:
        rollback_errors: list[str] = []
        for change in reversed(touched):
            try:
                if not change.dest.is_symlink():
                    raise OSError("rollback target became a non-symlink")
                if change.previous is None:
                    change.dest.unlink()
                else:
                    atomic_symlink(change.previous, change.dest)
            except OSError as rollback_exc:
                rollback_errors.append(f"{change.dest}: {rollback_exc}")
        if rollback_errors:
            print(f"linking failed and rollback was incomplete: {exc}", file=sys.stderr)
            for error in rollback_errors:
                print(f"- {error}", file=sys.stderr)
        else:
            print(f"linking failed; invocation changes were rolled back: {exc}", file=sys.stderr)
        return 3

    print(f"linked {len(plan)} skills; {len(names) - len(plan)} already correct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
