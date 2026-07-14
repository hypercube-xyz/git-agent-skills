#!/usr/bin/env python3
"""Inspect effective Git remote configuration without disclosing credentials.

The helper reads effective config with origin and scope. URL-like values are fail-closed:
recognized forms are sanitized; opaque forms are never echoed.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Union
from urllib.parse import urlsplit, urlunsplit

REMOTE_KEY = re.compile(r"^remote\.(.+)\.(url|pushurl|fetch)$", re.IGNORECASE)
SCP_LIKE = re.compile(r"^(?:(?P<user>[^@/:]+)@)?(?P<host>\[[^]]+\]|[^:/]+):(?P<path>.+)$")
SAFE_HOST = re.compile(r"^[A-Za-z0-9._-]+$|^\[[0-9A-Fa-f:]+\]$")


def run_config(repo: Path) -> bytes:
    cmd = [
        "git", "-C", str(repo), "config", "--null", "--show-origin", "--show-scope",
        "--get-regexp", r"^remote\..*\.(url|pushurl|fetch)$",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
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
    records: list[tuple[str, str, str, str]] = []
    for i in range(0, len(fields), 3):
        scope = fields[i].decode("utf-8", "replace")
        origin = fields[i + 1].decode("utf-8", "replace")
        key_value = fields[i + 2].decode("utf-8", "replace")
        if "\n" not in key_value:
            raise ValueError("missing key/value separator")
        key, value = key_value.split("\n", 1)
        records.append((scope, origin, key, value))
    return records


def sanitize_url(value: str) -> dict[str, Union[str, bool]]:
    """Return a sanitized representation. Never include query, fragment, or password."""
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        return {"display": "<redacted-opaque>", "classified": False}

    # Standard URLs. urlsplit also understands ssh:// and git://. Malformed
    # authority or port syntax is treated as opaque without aborting the inventory.
    try:
        parts = urlsplit(value)
        scheme = parts.scheme.lower()
        hostname = parts.hostname
        port_number = parts.port
    except ValueError:
        return {"display": "<redacted-opaque>", "classified": False}

    if parts.scheme:
        if scheme == "file":
            return {"display": "file://<redacted-local-path>", "classified": True}
        if scheme not in {"http", "https", "ssh", "git"} or not hostname:
            return {"display": "<redacted-opaque>", "classified": False}
        host = hostname
        if ":" in host and not host.startswith("["):
            host = f"[{host}]"
        port = f":{port_number}" if port_number else ""
        user = "<redacted-user>@" if parts.username is not None else ""
        path = parts.path or ""
        display = urlunsplit((scheme, f"{user}{host}{port}", path, "", ""))
        return {"display": display, "classified": True}

    # Git scp-like syntax: [user@]host:path. Avoid treating Windows drives as hosts.
    if re.match(r"^[A-Za-z]:[\\/]", value):
        return {"display": "<redacted-local-path>", "classified": True}
    match = SCP_LIKE.match(value)
    if match and SAFE_HOST.match(match.group("host")):
        user = "<redacted-user>@" if match.group("user") else ""
        return {"display": f"{user}{match.group('host')}:{match.group('path')}", "classified": True}

    # Relative/absolute filesystem paths can reveal usernames and workspace names.
    if value.startswith(('/', './', '../', '~')):
        return {"display": "<redacted-local-path>", "classified": True}
    return {"display": "<redacted-opaque>", "classified": False}


def inspect(repo: Path) -> dict[str, object]:
    remotes: dict[str, dict[str, list[dict[str, object]]]] = {}
    for scope, origin, key, value in parse_records(run_config(repo)):
        match = REMOTE_KEY.match(key)
        if not match:
            continue
        name, kind = match.groups()
        entry: dict[str, object] = {"scope": scope, "origin": origin}
        if kind.lower() == "fetch":
            entry.update({"value": value, "classified": True})
        else:
            entry.update(sanitize_url(value))
        remotes.setdefault(name, {"url": [], "pushurl": [], "fetch": []})[kind.lower()].append(entry)
    return {"repository": str(repo.resolve()), "remotes": remotes}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", nargs="?", default=".")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    try:
        payload = inspect(Path(args.repo))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"inspect-remotes: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
