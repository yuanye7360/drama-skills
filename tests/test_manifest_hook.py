"""The manifest refresh has to happen on commit, not in CI.

Every file under `skills/` is hashed into the suite manifest, so editing one and
committing without refreshing turns the installation-resolution tests red for a
reason unrelated to the change. The versioned pre-commit hook closes that gap;
these tests cover the parts that silently do nothing when wrong — a hook git
never runs because it is not executable, a `core.hooksPath` that was never set,
and a development-side mismatch message that does not name the fix.

What is not covered here: driving a real `git commit` through the hook. That
needs a full clone, and the behaviour it would assert (refresh then verify) is
already asserted by `test_suite_anatomy` and the refresher's own tests.
"""

from __future__ import annotations

import ast
import importlib.util
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
HOOK = SUITE / ".githooks" / "pre-commit"
INSTALLER = SUITE / "tools" / "install_hooks.py"

_spec = importlib.util.spec_from_file_location("install_hooks", INSTALLER)
assert _spec and _spec.loader
install_hooks = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(install_hooks)


class HookFileTests(unittest.TestCase):
    def test_hook_exists_and_is_executable(self) -> None:
        # git ignores a non-executable hook without a word, which is
        # indistinguishable from a hook that ran and found nothing to do.
        self.assertTrue(HOOK.is_file(), f"missing {HOOK}")
        self.assertTrue(
            HOOK.stat().st_mode & stat.S_IXUSR, f"{HOOK} is not executable"
        )

    def test_hook_is_posix_sh_not_bash(self) -> None:
        # Windows contributors get git-bash, which is POSIX sh; a bashism here
        # would fail only on their machines.
        self.assertEqual(HOOK.read_text(encoding="utf-8").splitlines()[0], "#!/bin/sh")

    def test_hook_exits_early_when_no_skill_file_is_staged(self) -> None:
        body = HOOK.read_text(encoding="utf-8")
        self.assertIn("--cached", body)
        self.assertIn("'^skills/'", body)
        self.assertIn("exit 0", body)

    def test_hook_verifies_after_refreshing(self) -> None:
        body = HOOK.read_text(encoding="utf-8")
        refresh = body.index("update_suite_manifest.py")
        verify = body.index("verify_suite.py")
        self.assertLess(refresh, verify, "the hook must verify after refreshing")


class InstallerTests(unittest.TestCase):
    def _repo(self, tmp: str) -> Path:
        repo = Path(tmp) / "checkout"
        (repo / ".githooks").mkdir(parents=True)
        hook = repo / ".githooks" / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        hook.chmod(0o644)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        return repo

    def _hooks_path(self, repo: Path) -> str:
        return subprocess.run(
            ["git", "-C", str(repo), "config", "--get", "core.hooksPath"],
            capture_output=True,
            text=True,
        ).stdout.strip()

    def test_install_sets_hooks_path_and_makes_hooks_executable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(tmp)
            changed, message = install_hooks.install(repo)
            self.assertTrue(changed, message)
            self.assertEqual(self._hooks_path(repo), ".githooks")
            mode = (repo / ".githooks" / "pre-commit").stat().st_mode
            self.assertTrue(mode & stat.S_IXUSR)

    def test_install_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._repo(tmp)
            install_hooks.install(repo)
            changed, message = install_hooks.install(repo)
            self.assertFalse(changed)
            self.assertIn("already", message)

    def test_missing_hooks_directory_is_reported_not_configured(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "bare"
            repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            changed, message = install_hooks.install(repo)
            self.assertFalse(changed)
            self.assertIn(".githooks", message)
            self.assertEqual(self._hooks_path(repo), "")


class DevelopmentMismatchMessageTests(unittest.TestCase):
    def test_dev_entrypoint_names_the_refresh_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Copy just enough of the tree that the verifier runs, then perturb
            # one shipped file so its hash no longer matches the manifest.
            checkout = Path(tmp) / "checkout"
            shutil.copytree(SUITE / "skills", checkout / "skills")
            shutil.copytree(SUITE / "tools", checkout / "tools")
            target = checkout / "skills" / "short-drama-write" / "SKILL.md"
            target.write_text(
                target.read_text(encoding="utf-8") + "\n<!-- perturbed -->\n",
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(checkout / "tools" / "verify_suite.py"),
                    "skills/short-drama",
                ],
                cwd=checkout,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
            self.assertIn("hash mismatch", result.stderr)
            self.assertIn("update_suite_manifest.py", result.stderr)
            self.assertIn("install_hooks.py", result.stderr)

    def test_shipped_verifier_does_not_advise_refreshing(self) -> None:
        # On a creator's machine a mismatch means a mixed or tampered install,
        # so telling them to refresh the manifest would launder it. The name may
        # appear in a comment aimed at maintainers; what must never happen is it
        # reaching a creator, which means no string literal may carry it.
        shipped = SUITE / "skills" / "short-drama" / "scripts" / "suite_verify.py"
        tree = ast.parse(shipped.read_text(encoding="utf-8"), filename=str(shipped))
        literals = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        offenders = [text for text in literals if "update_suite_manifest" in text]
        self.assertEqual(offenders, [], "the shipped verifier must not advise a refresh")


if __name__ == "__main__":
    unittest.main()
