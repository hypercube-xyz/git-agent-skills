#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_PARTS = {".git", "dist", "__pycache__"}
EXCLUDE_SUFFIXES = {".pyc"}


def files() -> list[Path]:
    result = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT)
        if any(part in EXCLUDE_PARTS for part in rel.parts):
            continue
        if path.suffix in EXCLUDE_SUFFIXES:
            continue
        result.append(rel)
    return sorted(result, key=lambda p: p.as_posix())


def build(destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    epoch = (2026, 1, 1, 0, 0, 0)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel in files():
            data = (ROOT / rel).read_bytes()
            info = zipfile.ZipInfo(rel.as_posix(), epoch)
            mode = 0o755 if os.access(ROOT / rel, os.X_OK) else 0o644
            info.external_attr = mode << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            zf.writestr(info, data)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    return digest


def run_checks() -> None:
    for script in ("validate_skills.py", "evaluate_fixtures.py"):
        subprocess.run(["python3", str(ROOT / "scripts" / script)], check=True, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "git-agent-skills.zip")
    args = parser.parse_args()
    run_checks()
    if args.check:
        with tempfile.TemporaryDirectory(prefix="git-agent-skills-build-") as raw:
            a = Path(raw) / "a.zip"
            b = Path(raw) / "b.zip"
            da = build(a)
            db = build(b)
            if a.read_bytes() != b.read_bytes() or da != db:
                raise SystemExit("release archive is not reproducible")
            print(f"PASS: reproducible archive ({len(files())} files, sha256 {da})")
        return 0
    digest = build(args.output)
    sidecar = args.output.with_suffix(args.output.suffix + ".sha256")
    sidecar.write_text(f"{digest}  {args.output.name}\n")
    print(args.output)
    print(digest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
