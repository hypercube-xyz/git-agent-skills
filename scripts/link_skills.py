#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
from typing import Optional

def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Link all packaged skills after an all-target preflight.")
    parser.add_argument("--target", type=Path, default=Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home()/".claude"))/"skills")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-symlinks", action="store_true", help="Replace foreign symlinks, never files/directories.")
    args = parser.parse_args()
    catalog = json.loads((root/"skills/catalog.json").read_text(encoding="utf-8"))
    names = [x["name"] for x in catalog["skills"]]
    target = args.target.expanduser().resolve(strict=False)
    plan: list[tuple[Path, Path, Optional[str]]] = []
    errors: list[str] = []
    for name in names:
        source = (root/"skills"/name).resolve(strict=True)
        dest = target/name
        if dest.is_symlink():
            current = os.readlink(dest)
            resolved = (dest.parent/current).resolve(strict=False)
            if resolved == source:
                continue
            if not args.force_symlinks:
                errors.append(f"foreign symlink: {dest} -> {current}")
            else:
                plan.append((source,dest,current))
        elif dest.exists():
            errors.append(f"refusing to replace non-symlink: {dest}")
        else:
            plan.append((source,dest,None))
    if errors:
        print("preflight failed; no changes made:", file=sys.stderr)
        for e in errors: print(f"- {e}", file=sys.stderr)
        return 2
    for source,dest,_old in plan:
        print(f"{'WOULD LINK' if args.dry_run else 'LINK'} {dest} -> {source}")
    if args.dry_run: return 0
    target.mkdir(parents=True, exist_ok=True)
    touched: list[tuple[Path, Optional[str]]] = []
    try:
        for source,dest,old in plan:
            touched.append((dest,old))
            if dest.is_symlink(): dest.unlink()
            dest.symlink_to(source, target_is_directory=True)
    except Exception as exc:
        rollback_errors: list[str] = []
        for dest,old in reversed(touched):
            try:
                if dest.is_symlink(): dest.unlink()
                elif dest.exists(): raise OSError("rollback target became a non-symlink")
                if old is not None: dest.symlink_to(old, target_is_directory=True)
            except OSError as rollback_exc:
                rollback_errors.append(f"{dest}: {rollback_exc}")
        if rollback_errors:
            print(f"linking failed and rollback was incomplete: {exc}", file=sys.stderr)
            for error in rollback_errors: print(f"- {error}", file=sys.stderr)
        else:
            print(f"linking failed; changes from this invocation were rolled back: {exc}", file=sys.stderr)
        return 3
    print(f"linked {len(plan)} skills; {len(names)-len(plan)} already correct")
    return 0
if __name__ == '__main__': raise SystemExit(main())
