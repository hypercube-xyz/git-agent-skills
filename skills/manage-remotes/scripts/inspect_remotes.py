#!/usr/bin/env python3
"""Print configured Git remotes with fail-closed credential redaction.

Requires Python 3.9+. Reads local Git configuration only and performs no network access.
Unknown or opaque address forms are redacted rather than echoed.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from urllib.parse import urlsplit, urlunsplit

SENSITIVE_QUERY = re.compile(
    r"(?i)(access[_-]?token|auth|authorization|credential|key|password|secret|signature|sig|token)"
)
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
SCP_LIKE = re.compile(r"^(?:(?P<user>[^/@:\s]+)@)?(?P<host>[^/:\s]+):(?P<path>.+)$")
HELPER = re.compile(r"^(?P<helper>[A-Za-z][A-Za-z0-9+.-]*)::(?P<address>.*)$")


def run_git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if proc.returncode:
        msg = CONTROL.sub("?", proc.stderr.strip())
        raise RuntimeError(msg or f"git exited with {proc.returncode}")
    return proc.stdout


def redact_url(value: str) -> str:
    value = CONTROL.sub("?", value.strip())
    if not value:
        return "<empty>"

    helper = HELPER.match(value)
    if helper:
        return f"{helper.group('helper')}::<redacted-opaque-address>"

    # Standard URL with a scheme.
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<redacted-unparseable-remote>"

    if parsed.scheme and parsed.netloc:
        host = parsed.hostname or "<redacted-host>"
        port = f":{parsed.port}" if parsed.port else ""
        # Never preserve userinfo. Preserve a bounded path for usability.
        path = parsed.path or ""
        if len(path) > 256:
            path = path[:253] + "..."
        safe_query_parts = []
        if parsed.query:
            for item in parsed.query.split("&"):
                key = item.split("=", 1)[0]
                safe_query_parts.append(f"{key}=<redacted>" if SENSITIVE_QUERY.search(key) else key)
        safe_query = "&".join(safe_query_parts)
        return urlunsplit((parsed.scheme, host + port, path, safe_query, ""))

    # scp-like SSH syntax. Drop userinfo and bound the path.
    match = SCP_LIKE.match(value)
    if match and not value.startswith(("/", "./", "../")):
        path = match.group("path")
        if "@" in path or CONTROL.search(path):
            path = "<redacted-path>"
        elif len(path) > 256:
            path = path[:253] + "..."
        return f"{match.group('host')}:{path}"

    # Local paths are useful but can reveal usernames/home locations. Report class only.
    if value.startswith(("/", "./", "../", "~")):
        return "<local-path>"

    return "<redacted-opaque-remote>"


def config_entries() -> list[dict[str, str]]:
    out = run_git("config", "--null", "--get-regexp", r"^remote\..*\.(url|pushurl|fetch)$")
    entries: list[dict[str, str]] = []
    for record in out.split("\0"):
        if not record:
            continue
        if "\n" in record:
            key, value = record.split("\n", 1)
        elif " " in record:
            key, value = record.split(" ", 1)
        else:
            entries.append({"key": CONTROL.sub("?", record), "value": "<missing>"})
            continue
        kind = key.rsplit(".", 1)[-1]
        safe = value if kind == "fetch" else redact_url(value)
        entries.append({"key": CONTROL.sub("?", key), "value": safe})
    return entries


def main() -> int:
    try:
        entries = config_entries()
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(entries, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
