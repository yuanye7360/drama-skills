#!/usr/bin/env python3
"""Point a checkout's git hooks at the versioned `.githooks/` directory.

`.git/hooks` is not versioned, so a hook committed to the repository does
nothing until each checkout opts in. One `core.hooksPath` setting does that for
every hook at once, and unlike copying files it cannot drift from what is
committed.

Idempotent: running it twice reports that the setting is already in place.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HOOKS_DIRNAME = ".githooks"


def install(repo: Path) -> tuple[bool, str]:
    """Set `core.hooksPath`. Returns (changed, message)."""
    hooks = repo / HOOKS_DIRNAME
    if not hooks.is_dir():
        return False, f"no {HOOKS_DIRNAME}/ directory in {repo}"

    current = subprocess.run(
        ["git", "-C", str(repo), "config", "--get", "core.hooksPath"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if current == HOOKS_DIRNAME:
        return False, f"core.hooksPath is already {HOOKS_DIRNAME}"

    subprocess.run(
        ["git", "-C", str(repo), "config", "core.hooksPath", HOOKS_DIRNAME],
        check=True,
    )
    # A hook that is not executable is silently ignored by git, which looks
    # exactly like a hook that ran and found nothing.
    for hook in hooks.iterdir():
        if hook.is_file():
            hook.chmod(hook.stat().st_mode | 0o111)
    was = f" (was {current!r})" if current else ""
    return True, f"core.hooksPath set to {HOOKS_DIRNAME}{was}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="checkout to configure; defaults to this script's repository",
    )
    args = parser.parse_args(argv)
    changed, message = install(args.repo.resolve())
    print(message)
    return 0 if changed or "already" in message else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
