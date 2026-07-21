#!/usr/bin/env python3
"""Deterministic security-contract checks for Git Agent Skills."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SKILL_HEADING = "## Untrusted Content and Execution"
MAILBOX_MARKER = "Hardened Ingestion Boundary"
errors: list[str] = []

# --- Static contract checks on skill files and docs ---

skill_files = sorted((ROOT / "skills").glob("*/SKILL.md"))
if not skill_files:
    errors.append("no skill packages found")
for path in skill_files:
    text = path.read_text(encoding="utf-8")
    if REQUIRED_SKILL_HEADING not in text:
        errors.append(f"{path.relative_to(ROOT)}: missing untrusted-content boundary")
    if "repository-controlled text" not in text:
        errors.append(f"{path.relative_to(ROOT)}: missing third-party content rule")
    if "unknown partial outcome" not in text:
        errors.append(f"{path.relative_to(ROOT)}: missing partial-outcome stop rule")

mailbox = ROOT / "skills/transplant-commits/references/patch-mailbox-workflows.md"
if not mailbox.is_file() or MAILBOX_MARKER not in mailbox.read_text(encoding="utf-8"):
    errors.append("transplant mailbox reference lacks hardened ingestion boundary")

security_doc = ROOT / "docs/SECURITY-EXECUTION.md"
if not security_doc.is_file():
    errors.append("docs/SECURITY-EXECUTION.md is missing")
else:
    doc = security_doc.read_text(encoding="utf-8")
    for phrase in (
        "Runtime-enforced controls",
        "Indirect prompt injection",
        "Unknown outcomes and retries",
        "Self-modification",
    ):
        if phrase not in doc:
            errors.append(f"security execution document missing: {phrase}")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
if "docs/SECURITY-EXECUTION.md" not in readme:
    errors.append("README does not link the execution security contract")


# --- Helpers ---

def clean_env(repo: Path) -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "TMPDIR", "TMP", "TEMP", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT"}
        or key == "LANG"
        or key.startswith("LC_")
    }
    env.update(
        {
            "HOME": str(repo / "isolated-home"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "GIT_TEMPLATE_DIR": str(repo / "empty-template"),
        }
    )
    Path(env["HOME"]).mkdir()
    Path(env["GIT_TEMPLATE_DIR"]).mkdir()
    return env


def import_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# --- A. Git environment isolation (behavior) ---

def env_isolation_test() -> None:
    with tempfile.TemporaryDirectory(prefix="env-iso-test-") as td:
        repo = Path(td)
        (repo / "scripts").mkdir()
        import shutil
        shutil.copy2(ROOT / "scripts/security_git_env.py", repo / "scripts/security_git_env.py")
        sys.path.insert(0, str(repo / "scripts"))
        try:
            env_mod = import_module("env_iso", repo / "scripts/security_git_env.py")

            sanitized = env_mod.controlled_git_env(
                {
                    "PATH": os.environ.get("PATH", ""),
                    "HOME": str(repo / "h"),
                    "GNUPGHOME": "/secret/gpg",
                    "GPG_TTY": "/dev/tty",
                    "SSL_CERT_FILE": "/secret/ca.pem",
                    "SSL_CERT_DIR": "/secret/ca",
                    "SSH_AUTH_SOCK": "/secret/agent",
                }
            )
            for key in ("GPG_TTY", "SSL_CERT_FILE", "SSL_CERT_DIR", "SSH_AUTH_SOCK", "GNUPGHOME"):
                if key in sanitized:
                    raise AssertionError(f"sensitive env var {key} survived")

            if "core.fsmonitor" not in sanitized.get("GIT_CONFIG_KEY_0", ""):
                raise AssertionError("fsmonitor not disabled")
            if "core.hooksPath" not in sanitized.get("GIT_CONFIG_KEY_2", ""):
                raise AssertionError("hooksPath not overridden by default")
            if sanitized.get("GIT_CONFIG_COUNT") != "3":
                raise AssertionError(f"expected 3 config overrides, got {sanitized.get('GIT_CONFIG_COUNT')}")

            hook_env = {"PATH": os.environ.get("PATH", ""), "HOME": str(repo / "h"),
                        "GIT_AGENT_SKILLS_ALLOW_HOOKS": "1"}
            sanitized_hook = env_mod.controlled_git_env(hook_env)
            if sanitized_hook.get("GIT_CONFIG_COUNT") != "2":
                raise AssertionError("hooks opt-in should have fsmonitor+autocrlf only")

            gnupg_env = {"PATH": os.environ.get("PATH", ""), "HOME": str(repo / "h"),
                         "GNUPGHOME": "/secret/gpg", "GIT_AGENT_SKILLS_ALLOW_GNUPGHOME": "1"}
            sanitized_gnupg = env_mod.controlled_git_env(gnupg_env)
            if sanitized_gnupg.get("GNUPGHOME") != "/secret/gpg":
                raise AssertionError("GNUPGHOME not preserved with opt-in")

            import inspect
            docstring = inspect.getdoc(env_mod.resolve_git)
            if "trusted input" not in docstring:
                raise AssertionError("resolve_git docstring does not document PATH as trusted")
        finally:
            sys.modules.pop("env_iso", None)
            sys.path.remove(str(repo / "scripts"))


try:
    env_isolation_test()
except Exception as exc:
    errors.append(f"env isolation behavior test failed: {exc}")


# --- B. Package integrity (behavior) ---

def package_integrity_test() -> None:
    with tempfile.TemporaryDirectory(prefix="pkg-integrity-") as td:
        repo = Path(td)
        (repo / "scripts").mkdir()
        (repo / "skills").mkdir()
        for name in ("build_release.py", "security_git_env.py"):
            (repo / "scripts" / name).write_bytes((ROOT / "scripts" / name).read_bytes())
        catalog_path = repo / "skills/catalog.json"
        catalog_path.write_text(
            json.dumps({"package_version": "0.0.0", "release_date": "2026-07-21",
                        "skills": [], "compatibility": {}}),
            encoding="utf-8",
        )
        payload = repo / "payload.txt"
        committed = b"committed\n"
        dirty = b"dirty\n"
        payload.write_bytes(committed)
        env = clean_env(repo)
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "config", "user.email", "t@e"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=repo, check=True, env=env)
        subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
        subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True, env=env)

        payload.write_bytes(dirty)
        (repo / ".env").write_bytes(b"SECRET=leak\n")

        sys.path.insert(0, str(repo / "scripts"))
        try:
            mod = import_module("pkg_build", repo / "scripts/build_release.py")

            for unsafe in (b"../escape", b"a//b", b"a\\b", b"CON.txt", b"bad\x1bname"):
                try:
                    mod.validate_path(unsafe)
                except SystemExit:
                    pass
                else:
                    raise AssertionError(f"unsafe path accepted: {unsafe!r}")

            output = repo.parent / f"{repo.name}-artifact.zip"
            old_argv = sys.argv
            sys.argv = ["build_release.py", "--output", str(output)]
            try:
                assert mod.main() == 0
            finally:
                sys.argv = old_argv
            with zipfile.ZipFile(output) as archive:
                archived = archive.read("git-agent-skills-0.0.0/payload.txt")
                archived_names = archive.namelist()
            if archived == dirty:
                raise AssertionError(
                    f"archive used dirty working-tree bytes: {archived!r}"
                )
            if archived != committed:
                raise AssertionError(
                    f"archive committed bytes mismatch: "
                    f"expected={committed!r}, actual={archived!r}"
                )
            if any(".env" in name for name in archived_names):
                raise AssertionError("untracked .env leaked into archive")

            rev = mod.source_revision(root=repo)
            entries = mod.tracked_files(rev, root=repo)
            catalog = mod.catalog_from_entries(entries)
            assert mod.archive_bytes(entries, catalog) == mod.archive_bytes(entries, catalog)

            import inspect
            src = inspect.getsource(mod)
            if "VALIDATION" in src or "validate_skills" in src:
                raise AssertionError("builder still contains validation orchestration")
            if "skip_validation" in src:
                raise AssertionError("builder still has --skip-validation")
        finally:
            for n in ("pkg_build", "security_git_env"):
                sys.modules.pop(n, None)
            sys.path.remove(str(repo / "scripts"))


try:
    package_integrity_test()
except Exception as exc:
    errors.append(f"package integrity behavior test failed: {exc}")


# --- C. Destination safety (behavior) ---

def destination_safety_test() -> None:
    with tempfile.TemporaryDirectory(prefix="dest-safety-") as td:
        repo = Path(td)
        (repo / "scripts").mkdir()
        import shutil
        shutil.copy2(ROOT / "scripts/build_release.py", repo / "scripts/build_release.py")
        shutil.copy2(ROOT / "scripts/security_git_env.py", repo / "scripts/security_git_env.py")
        sys.path.insert(0, str(repo / "scripts"))
        try:
            mod = import_module("dest_build", repo / "scripts/build_release.py")

            outside = repo / "outside"
            outside.mkdir()
            redirect = repo / "redirect"
            redirect.symlink_to(outside, target_is_directory=True)
            try:
                mod.reject_symlink_components(redirect / "release.zip")
            except SystemExit:
                pass
            else:
                raise AssertionError("symlinked output parent accepted")

            if sys.platform == "darwin":
                assert Path("/tmp") in mod._TRUSTED_SYMLINKS
                assert mod._TRUSTED_SYMLINKS[Path("/tmp")] == Path("/private/tmp")
            else:
                assert not mod._TRUSTED_SYMLINKS, "trusted symlinks should be empty on non-macOS"
        finally:
            for n in ("dest_build", "security_git_env"):
                sys.modules.pop(n, None)
            sys.path.remove(str(repo / "scripts"))


try:
    destination_safety_test()
except Exception as exc:
    errors.append(f"destination safety behavior test failed: {exc}")


# --- D. Installer mode (behavior) ---

def installer_mode_test() -> None:
    import inspect
    src = (ROOT / "scripts/link_skills.py").read_text(encoding="utf-8")
    if "--mode" not in src:
        raise AssertionError("linker does not have --mode argument")
    if "atomic_copy" not in src:
        raise AssertionError("linker does not have copy fallback")
    if "can_symlink" not in src:
        raise AssertionError("linker does not have symlink capability check")
    if "target_input.is_symlink()" not in src:
        raise AssertionError("linker does not check raw symlink before resolve()")


try:
    installer_mode_test()
except Exception as exc:
    errors.append(f"installer mode behavior test failed: {exc}")


# --- E. Release reconciliation (behavior) ---

def release_reconciliation_test() -> None:
    release_yml = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    if "Failing closed" not in release_yml:
        errors.append("release workflow does not fail closed on digest mismatch")
    if "--clobber" in release_yml:
        errors.append("release workflow still uses --clobber")
    if "--output -" not in release_yml:
        errors.append("release workflow does not use --output - for streaming download")


try:
    release_reconciliation_test()
except Exception as exc:
    errors.append(f"release reconciliation behavior test failed: {exc}")


# --- CI matrix check ---

def ci_matrix_test() -> None:
    validate_yml = (ROOT / ".github/workflows/validate.yml").read_text(encoding="utf-8")
    for os_name in ("ubuntu-latest", "macos-latest", "windows-latest"):
        if os_name not in validate_yml:
            errors.append(f"CI does not test on {os_name}")
    if "Run security regression tests" not in validate_yml:
        errors.append("CI does not run security regression tests")
    if 'GIT_CONFIG_NOSYSTEM: "1"' not in validate_yml:
        errors.append("CI lacks controlled Git system-config boundary")


try:
    ci_matrix_test()
except Exception as exc:
    errors.append(f"CI matrix test failed: {exc}")


if errors:
    for error in errors:
        print(f"FAIL: {error}")
    raise SystemExit(1)

print(f"PASS: security contract and regressions ({len(skill_files)} skills)")
