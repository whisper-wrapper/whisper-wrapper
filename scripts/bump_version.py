#!/usr/bin/env python3
"""Sync and bump project version in src/meta.py and pyproject.toml."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META_FILE = ROOT / "src" / "meta.py"
PYPROJECT_FILE = ROOT / "pyproject.toml"

META_VERSION_RE = re.compile(r'^(APP_VERSION\s*=\s*["\'])(\d+\.\d+\.\d+)(["\'])', re.M)
PYPROJECT_VERSION_RE = re.compile(r'^(version\s*=\s*["\'])(\d+\.\d+\.\d+)(["\'])', re.M)
SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _read_version(path: Path, pattern: re.Pattern[str]) -> str:
    text = path.read_text(encoding="utf-8")
    match = pattern.search(text)
    if not match:
        raise ValueError(f"Version not found in {path}")
    return match.group(2)


def _write_version(path: Path, pattern: re.Pattern[str], new_version: str) -> None:
    text = path.read_text(encoding="utf-8")
    updated, count = pattern.subn(
        lambda m: f"{m.group(1)}{new_version}{m.group(3)}",
        text,
        count=1,
    )
    if count != 1:
        raise ValueError(f"Failed to update version in {path}")
    path.write_text(updated, encoding="utf-8")


def _parse_semver(version: str) -> tuple[int, int, int]:
    match = SEMVER_RE.match(version)
    if not match:
        raise ValueError(f"Invalid version: {version} (expected X.Y.Z)")
    return tuple(int(part) for part in match.groups())


def _bump(version: str, bump: str) -> str:
    major, minor, patch = _parse_semver(version)
    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    if bump == "patch":
        return f"{major}.{minor}.{patch + 1}"
    raise ValueError(f"Unknown bump type: {bump}")


def _git_available() -> bool:
    try:
        subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--git-dir"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _git_tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "tag", "--list", tag],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return tag in (result.stdout or "")


def _create_git_tag(version: str) -> None:
    tag = f"v{version}"
    if _git_tag_exists(tag):
        print(f"Tag {tag} already exists; skipping.")
        return
    subprocess.run(["git", "-C", str(ROOT), "tag", tag], check=True)
    print(f"Created tag {tag}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bump version in src/meta.py and pyproject.toml."
    )
    parser.add_argument(
        "version",
        nargs="?",
        help="Explicit version (X.Y.Z). If omitted, use --bump.",
    )
    parser.add_argument(
        "--bump",
        choices=["major", "minor", "patch"],
        help="Bump version based on current value.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show changes without writing files or tagging.",
    )
    tag_group = parser.add_mutually_exclusive_group()
    tag_group.add_argument("--tag", dest="tag", action="store_true")
    tag_group.add_argument("--no-tag", dest="tag", action="store_false")
    parser.set_defaults(tag=True)
    args = parser.parse_args()

    meta_version = _read_version(META_FILE, META_VERSION_RE)
    pyproject_version = _read_version(PYPROJECT_FILE, PYPROJECT_VERSION_RE)
    if meta_version != pyproject_version:
        print(
            f"Warning: version mismatch (meta={meta_version}, pyproject={pyproject_version})"
        )

    if args.version:
        new_version = args.version
        _parse_semver(new_version)
    elif args.bump:
        new_version = _bump(meta_version, args.bump)
    else:
        print("Error: provide a version or --bump.")
        return 2

    if args.dry_run:
        print(f"Would set version to {new_version}")
        return 0

    _write_version(META_FILE, META_VERSION_RE, new_version)
    _write_version(PYPROJECT_FILE, PYPROJECT_VERSION_RE, new_version)
    print(f"Updated version to {new_version}")

    if args.tag:
        if _git_available():
            _create_git_tag(new_version)
        else:
            print("Git repository not found; skipping tag.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
