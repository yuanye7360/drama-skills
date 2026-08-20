#!/usr/bin/env python3
"""Development entrypoint for the verifier shipped with short-drama."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


IMPLEMENTATION = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "short-drama"
    / "scripts"
    / "suite_verify.py"
)


def _load_implementation() -> ModuleType:
    spec = importlib.util.spec_from_file_location("short_drama_suite_verify", IMPLEMENTATION)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load suite verifier: {IMPLEMENTATION}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_IMPL = _load_implementation()


def verify_suite(core: Path) -> dict[str, Any]:
    return _IMPL.verify_suite(core)


# Every failure that a stale manifest can produce. A file edited under skills/
# changes its hash; a file added or deleted changes the file set.
_STALE_MANIFEST_SIGNS = (
    "hash mismatch",
    "unexpected suite files",
    "missing manifest files",
)

_DEV_HINT = (
    "\nIn a development checkout this normally means the tree under skills/ "
    "changed without the manifest being refreshed. Run:\n"
    "  python3 tools/update_suite_manifest.py skills/short-drama\n"
    "and commit the refreshed manifest alongside the change. "
    "`python3 tools/install_hooks.py` makes that happen on commit."
)


def main(argv: list[str] | None = None) -> int:
    # This deliberately does not delegate to the shipped `main`. That one is
    # terse on purpose: on a creator's machine a mismatch means a mixed or
    # tampered install, and "refresh the manifest" would launder exactly what
    # the check exists to catch. In this repository the same failure almost
    # always means a forgotten refresh, so the hint belongs here and nowhere
    # near the installed script.
    core = Path(argv[0]) if argv else IMPLEMENTATION.parents[1]
    try:
        print(json.dumps(verify_suite(core), ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        if any(sign in str(error) for sign in _STALE_MANIFEST_SIGNS):
            print(_DEV_HINT, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
