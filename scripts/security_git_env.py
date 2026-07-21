#!/usr/bin/env python3
"""Controlled environment for repository validation and packaging tools.

This module is intentionally scoped to deterministic maintenance scripts. It is
not a universal wrapper for end-user Git workflows, where identity, signing,
hooks, credential configuration, and network trust may be part of the request.
"""
from __future__ import annotations

import atexit
import os
import shutil
import stat
import tempfile
from pathlib import Path
from typing import Mapping

_TEMP_ROOT = Path(tempfile.mkdtemp(prefix="git-agent-skills-env-"))
_HOME = _TEMP_ROOT / "home"
_TEMPLATE = _TEMP_ROOT / "empty-template"
_HOME.mkdir(mode=0o700)
_TEMPLATE.mkdir(mode=0o700)
atexit.register(lambda: shutil.rmtree(_TEMP_ROOT, ignore_errors=True))


def resolve_git(explicit: str | os.PathLike[str] | None = None) -> str:
    """Resolve Git to an absolute regular executable.

    When no explicit path is given, the Git executable is discovered via
    ``shutil.which("git")`` using the process ``PATH``. ``PATH`` is treated
    as a trusted input — callers responsible for release security must ensure
    ``PATH`` does not contain untrusted directories. For a hardened guarantee,
    pass an absolute executable path explicitly.
    """
    candidate = Path(explicit).expanduser() if explicit is not None else None
    if candidate is None:
        found = shutil.which("git")
        if not found:
            raise RuntimeError("git executable was not found")
        candidate = Path(found)
    candidate = candidate.resolve(strict=True)
    mode = candidate.stat().st_mode
    if not stat.S_ISREG(mode) or not os.access(candidate, os.X_OK):
        raise RuntimeError(f"git executable is not a regular executable: {candidate}")
    return str(candidate)


def controlled_git_env(base: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return a non-interactive environment isolated from ambient Git config.

    A caller-supplied fixture environment may intentionally opt into its HOME
    with ``GIT_AGENT_SKILLS_ALLOW_HOME=1``, into caller-installed hooks with
    ``GIT_AGENT_SKILLS_ALLOW_HOOKS=1``, or into a caller-managed signing home
    with ``GIT_AGENT_SKILLS_ALLOW_GNUPGHOME=1``. Ambient process state cannot
    enable any of these exceptions. CA overrides, askpass programs, SSH agents,
    credential variables, and Git config-injection variables are not inherited.
    """
    source = dict(os.environ if base is None else base)
    is_fixture = base is not None
    allow_home = is_fixture and source.pop("GIT_AGENT_SKILLS_ALLOW_HOME", "") == "1"
    allow_hooks = is_fixture and source.pop("GIT_AGENT_SKILLS_ALLOW_HOOKS", "") == "1"
    allow_gnupg = is_fixture and source.pop("GIT_AGENT_SKILLS_ALLOW_GNUPGHOME", "") == "1"
    requested_home = source.get("HOME") if allow_home else None
    requested_gnupghome = source.get("GNUPGHOME") if allow_gnupg else None

    allowed_exact = {
        "PATH", "TMPDIR", "TMP", "TEMP", "SYSTEMROOT", "WINDIR",
        "COMSPEC", "PATHEXT", "TERM",
    }
    env = {
        key: value
        for key, value in source.items()
        if key in allowed_exact or key == "LANG" or key.startswith("LC_")
    }
    config_count = 2
    env.update(
        {
            "HOME": requested_home or str(_HOME),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_TEMPLATE_DIR": str(_TEMPLATE),
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "PAGER": "cat",
            "GIT_EDITOR": ":",
            "GIT_SEQUENCE_EDITOR": ":",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_CONFIG_COUNT": "0",  # set below after counting
            "GIT_CONFIG_KEY_0": "core.fsmonitor",
            "GIT_CONFIG_VALUE_0": "false",
            "GIT_CONFIG_KEY_1": "core.autocrlf",
            "GIT_CONFIG_VALUE_1": "false",
            "LC_ALL": env.get("LC_ALL", "C"),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    if not allow_hooks:
        env[f"GIT_CONFIG_KEY_{config_count}"] = "core.hooksPath"
        env[f"GIT_CONFIG_VALUE_{config_count}"] = str(_TEMPLATE)
        config_count += 1
    env["GIT_CONFIG_COUNT"] = str(config_count)
    if requested_gnupghome:
        env["GNUPGHOME"] = requested_gnupghome
    return env
