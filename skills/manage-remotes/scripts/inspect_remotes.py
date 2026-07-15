#!/usr/bin/env python3
"""Inspect effective Git remote configuration without disclosing credentials."""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path
from typing import Union
from urllib.parse import urlsplit, urlunsplit

REMOTE_KEY = re.compile(r"^remote\.(.+)\.(url|pushurl|fetch)$", re.IGNORECASE)
SCP_LIKE = re.compile(
    r"^(?:(?P<user>[^@/:]+)@)?(?P<host>\[[^]]+\]|[^:/]+):(?P<path>.+)$"
)
SAFE_HOST = re.compile(r"^[A-Za-z0-9._-]+$|^\[[0-9A-Fa-f:]+\]$")


def run_config(repo: Path) -> bytes:
    proc = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "config",
            "--null",
            "--show-origin",
            "--show-scope",
            "--get-regexp",
            r"^remote\..*\.(url|pushurl|fetch)$",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode == 1 and not proc.stdout:
        return b""
    if proc.returncode != 0:
        raise RuntimeError("git config inspection failed")
    return proc.stdout


def parse_records(raw: bytes) -> list[tuple[str, str, str, str]]:
    fields = raw.split(b"\0")
    if fields and fields[-1] == b"":
        fields.pop()
    if len(fields) % 3:
        raise ValueError("unexpected git config --null output")
    records = []
    for i in range(0, len(fields), 3):
        scope = fields[i].decode("utf-8", "replace")
        origin = fields[i + 1].decode("utf-8", "replace")
        kv = fields[i + 2].decode("utf-8", "replace")
        if "\n" not in kv:
            raise ValueError("missing key/value separator")
        key, value = kv.split("\n", 1)
        records.append((scope, origin, key, value))
    return records


def sanitize_url(value: str) -> dict[str, Union[str, bool]]:
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return {"display": "", "classified": False}
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return {"display": value, "classified": True}
    try:
        parts = urlsplit(value)
        scheme = parts.scheme.lower()
        hostname = parts.hostname
        port_number = parts.port
    except ValueError:
        return {"display": "", "classified": False}
    if parts.scheme:
        if scheme == "file":
            if parts.username is not None or parts.password is not None:
                return {"display": "", "classified": False}
            return {
                "display": urlunsplit((scheme, parts.netloc, parts.path, "", "")),
                "classified": True,
            }
        if scheme not in {"http", "https", "ssh", "git"} or not hostname:
            return {"display": "", "classified": False}
        host = (
            hostname
            if ":" not in hostname or hostname.startswith("[")
            else f"[{hostname}]"
        )
        port = f":{port_number}" if port_number else ""
        user = "@" if parts.username is not None else ""
        path = parts.path or ""
        return {
            "display": urlunsplit((scheme, f"{user}{host}{port}", path, "", "")),
            "classified": True,
        }
    match = SCP_LIKE.match(value)
    if match and SAFE_HOST.match(match.group("host")):
        return {
            "display": f"{'@' if match.group('user') else ''}{match.group('host')}:{match.group('path')}",
            "classified": True,
        }
    if value.startswith(("/", "./", "../", "~")):
        return {"display": value, "classified": True}
    return {"display": "", "classified": False}


def inspect(repo: Path) -> dict[str, object]:
    remotes: dict[str, dict[str, list[dict[str, object]]]] = {}
    for scope, origin, key, value in parse_records(run_config(repo)):
        match = REMOTE_KEY.match(key)
        if not match:
            continue
        name, kind = match.groups()
        kind = kind.lower()
        entry: dict[str, object] = {"scope": scope, "origin": origin}
        entry.update(
            {"value": value, "classified": True}
            if kind == "fetch"
            else sanitize_url(value)
        )
        remotes.setdefault(name, {"url": [], "pushurl": [], "fetch": []})[kind].append(
            entry
        )
    return {"repository": str(repo.resolve()), "remotes": remotes}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--compact", action="store_true")
    a = p.parse_args()
    try:
        payload = inspect(Path(a.repo))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"inspect-remotes: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=None if a.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
