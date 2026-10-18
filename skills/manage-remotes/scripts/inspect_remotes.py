#!/usr/bin/env python3
"""Inspect configured URLs/refspecs and effective URLs, redacting URL secrets.

Paths, hosts, remote names and config origins remain visible. This is not a
general secret detector; do not display its output if those fields are sensitive.
The repo argument selects the repository; ambient repository and config-file
selectors are ignored. Other config, including includes and rewrites, is retained.
"""
from __future__ import annotations
import argparse, json, os, re, subprocess, sys
from pathlib import Path
from typing import Union
from urllib.parse import urlsplit, urlunsplit

REMOTE_KEY = re.compile(r"^remote\.(.+)\.(url|pushurl|fetch|push)$", re.IGNORECASE)
SCP_LIKE = re.compile(
    r"^(?:(?P<user>[^@/:]+)@)?(?P<host>\[[^]]+\]|[^:/]+):(?P<path>.+)$"
)
SAFE_HOST = re.compile(r"^[A-Za-z0-9._-]+$|^\[[0-9A-Fa-f:]+\]$")


def inspection_env() -> dict[str, str]:
    # GIT_CONFIG redirects only `git config`, making it disagree with get-url.
    # Keep both inspections on the selected repo's effective configuration.
    selectors = {"GIT_DIR", "GIT_COMMON_DIR", "GIT_WORK_TREE", "GIT_CONFIG"}
    return {key: value for key, value in os.environ.items()
            if key.upper() not in selectors}


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
            r"^(remote\..*\.(url|pushurl|fetch|push)|url\..*\.(insteadof|pushinsteadof))$",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=15,
        env=inspection_env(),
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
    # Git's SSH grammar allows an omitted username; urlsplit instead interprets
    # host:path as a scheme. Do not admit explicit remote-helper transport:: forms.
    match = SCP_LIKE.match(value) if "://" not in value else None
    if match and SAFE_HOST.fullmatch(match.group("host")) and not match.group("path").startswith(":"):
        return {
            "display": f"{'@' if match.group('user') else ''}{match.group('host')}:{match.group('path')}",
            "classified": True,
        }
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
        port = f":{port_number}" if port_number is not None else ""
        user = "@" if parts.username is not None else ""
        path = parts.path or ""
        return {
            "display": urlunsplit((scheme, f"{user}{host}{port}", path, "", "")),
            "classified": True,
        }
    if value.startswith(("/", "./", "../", "~")):
        return {"display": value, "classified": True}
    return {"display": "", "classified": False}


def effective_urls(repo: Path, name: str, push: bool) -> list[dict[str, Union[str, bool]]]:
    # Git owns longest-prefix rewrite and explicit-pushurl precedence. No network.
    proc = subprocess.run(
        ["git", "-C", str(repo), "remote", "get-url", "--all",
         *(["--push"] if push else []), "--", name],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=15,
        env=inspection_env(),
    )
    if proc.returncode:
        return [{"display": "", "classified": False}]
    # get-url uses LF, not Unicode's broader splitlines separators. Preflight
    # rejects embedded ASCII controls; preserve Unicode bytes in actual records.
    output = proc.stdout.decode("utf-8", "strict")
    if not output.endswith("\n"):
        return [{"display": "", "classified": False}]
    return [sanitize_url(value) for value in output[:-1].split("\n")]


def inspect(repo: Path) -> dict[str, object]:
    remotes: dict[str, dict[str, list[dict[str, object]]]] = {}
    records = parse_records(run_config(repo))
    # get-url is line-delimited: reject controls before interpreting its records,
    # including rewrite keys/values which could introduce a hidden extra line.
    unsafe_lines = any(any(ord(ch) < 32 or ord(ch) == 127 for ch in key + value)
                       for _, _, key, value in records)
    for scope, origin, key, value in records:
        match = REMOTE_KEY.match(key)
        if not match:
            continue
        name, kind = match.groups()
        kind = kind.lower()
        entry: dict[str, object] = {"scope": scope, "origin": origin}
        entry.update(
            {"value": value, "classified": True}
            if kind in {"fetch", "push"}
            else sanitize_url(value)
        )
        remotes.setdefault(name, {"url": [], "pushurl": [], "fetch": [], "push": []})[kind].append(
            entry
        )
    for name, remote in remotes.items():
        for label, push in (("effective_fetch", False), ("effective_push", True)):
            remote[label] = ([{"display": "", "classified": False}] if unsafe_lines
                             else effective_urls(repo, name, push))
    return {"repository": str(repo.resolve()), "remotes": remotes}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--compact", action="store_true")
    a = p.parse_args()
    try:
        payload = inspect(Path(a.repo))
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        print("inspect-remotes: inspection failed; raw config and command output withheld", file=sys.stderr)
        return 2
    print(json.dumps(payload, indent=None if a.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
