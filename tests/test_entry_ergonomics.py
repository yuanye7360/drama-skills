"""One way in, and one spelling for the project path.

Two frictions this covers, both measured while driving the suite by hand:

1. `project_tool.py` takes the project positionally while every renderer takes
   it as `--project`. Guessing wrong costs a round trip on a command whose only
   job is to report state, and the two spellings live one directory apart.
2. Entering a stage means three commands in a fixed order — verify the install,
   finish interrupted publications, read status — and the order matters: status
   read before recovery can describe a project that is mid-write.

`enter` is that sequence as one call. It is not allowed to soften what the
sequence protects: a blocked recovery has to stay the reported next action
rather than being buried under an otherwise healthy-looking status.
"""

from __future__ import annotations

import contextlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
SCRIPT = SUITE / "skills/short-drama/scripts/project_tool.py"
_SPEC = importlib.util.spec_from_file_location("short_drama_entry", SCRIPT)
assert _SPEC and _SPEC.loader
project_tool = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(project_tool)


class ProjectPathSpellingTests(unittest.TestCase):
    def _project(self, tmp: str) -> Path:
        root = Path(tmp) / "项目"
        project_tool.initialize_project(
            root,
            title="入口",
            language="zh-CN",
            aspect_ratio="9:16",
            suite_root=SUITE / "skills/short-drama",
        )
        return root

    def _run(self, argv: list[str]) -> tuple[int, str]:
        import io

        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = project_tool.main(argv)
            except SystemExit as exit_error:  # argparse errors
                code = int(exit_error.code or 0)
        return code, out.getvalue() + err.getvalue()

    def test_positional_path_still_works(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            code, output = self._run(["status", str(root)])
            self.assertEqual(code, 0, output)
            self.assertEqual(json.loads(output)["project_root"], str(root.resolve()))

    def test_project_flag_is_accepted_as_the_same_thing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            code, output = self._run(["status", "--project", str(root)])
            self.assertEqual(code, 0, output)
            self.assertEqual(json.loads(output)["project_root"], str(root.resolve()))

    def test_recover_accepts_the_flag_too(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            code, output = self._run(["recover", "--project", str(root)])
            self.assertEqual(code, 0, output)
            self.assertEqual(json.loads(output)["project_root"], str(root.resolve()))

    def test_two_different_paths_are_refused_not_silently_picked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            other = Path(tmp) / "另一个"
            other.mkdir()
            code, output = self._run(["status", str(root), "--project", str(other)])
            self.assertNotEqual(code, 0)
            self.assertIn("--project", output)

    def test_the_same_path_twice_is_not_a_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            code, output = self._run(["status", str(root), "--project", str(root)])
            self.assertEqual(code, 0, output)

    def test_a_command_that_needs_a_path_says_both_spellings(self) -> None:
        code, output = self._run(["verify", "--episode", "EP001"])
        self.assertNotEqual(code, 0)
        self.assertIn("--project", output)


class EnterTests(unittest.TestCase):
    """`enter`'s own behaviour.

    The install check is stubbed wherever it is not the subject: those cases are
    about recovery/status order and about `next_action`, and tying them to the
    working tree's manifest freshness would make an unrelated documentation edit
    look like a broken sequence.
    """

    PASSING_INSTALL = {"suite": "short-drama-suite", "checked_files": 0}

    @contextlib.contextmanager
    def stub_install(self):
        real = project_tool._verify_installation
        project_tool._verify_installation = lambda: dict(self.PASSING_INSTALL)
        try:
            yield
        finally:
            project_tool._verify_installation = real

    def _project(self, tmp: str) -> Path:
        root = Path(tmp) / "项目"
        project_tool.initialize_project(
            root,
            title="入口",
            language="zh-CN",
            aspect_ratio="9:16",
            suite_root=SUITE / "skills/short-drama",
        )
        return root

    def test_enter_reports_install_recovery_and_status_together(self) -> None:
        # The one case that runs the real verifier: `enter` must report the
        # shipped verifier's own answer, not a restatement of it. It therefore
        # needs a fresh manifest, which test_suite_anatomy already enforces.
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            result = project_tool.enter_project(root)
            self.assertEqual(result["install"]["suite"], "short-drama-suite")
            self.assertEqual(result["status"]["project_root"], str(root.resolve()))
            self.assertEqual(result["recovery"]["blocked"], 0)
            self.assertEqual(result["next_action"], "continue")

    def test_status_is_read_after_recovery_not_before(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.stub_install():
            root = self._project(tmp)
            order: list[str] = []
            real_recover = project_tool.recover_project
            real_status = project_tool.project_status

            def traced_recover(path: Path) -> dict[str, object]:
                order.append("recover")
                return real_recover(path)

            def traced_status(path: Path) -> dict[str, object]:
                order.append("status")
                return real_status(path)

            project_tool.recover_project = traced_recover
            project_tool.project_status = traced_status
            try:
                project_tool.enter_project(root)
            finally:
                project_tool.recover_project = real_recover
                project_tool.project_status = real_status
            self.assertEqual(order, ["recover", "status"])

    def test_blocked_recovery_stays_the_next_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, self.stub_install():
            root = self._project(tmp)
            real_recover = project_tool.recover_project

            def blocked(path: Path) -> dict[str, object]:
                result = dict(real_recover(path))
                result["blocked"] = 1
                return result

            project_tool.recover_project = blocked
            try:
                result = project_tool.enter_project(root)
            finally:
                project_tool.recover_project = real_recover
            # An otherwise healthy status must not read as "go ahead" while a
            # publication is stuck half-written.
            self.assertEqual(result["next_action"], "resolve_blocked_transactions")

    def test_a_bad_install_stops_before_recovery_writes_anything(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(tmp)
            touched: list[str] = []
            real_recover = project_tool.recover_project
            real_verify = project_tool._verify_installation

            def must_not_run(path: Path) -> dict[str, object]:
                touched.append("recover")
                return real_recover(path)

            def broken_install() -> dict[str, object]:
                raise ValueError("content hash mismatch: short-drama/SKILL.md")

            project_tool.recover_project = must_not_run
            project_tool._verify_installation = broken_install
            try:
                result = project_tool.enter_project(root)
            finally:
                project_tool.recover_project = real_recover
                project_tool._verify_installation = real_verify
            self.assertEqual(result["next_action"], "fix_installation")
            self.assertEqual(result["install"]["status"], "failed")
            self.assertIn("hash mismatch", result["install"]["error"])
            # Recovery finishes half-written transactions in creator files. An
            # install we cannot vouch for does not get to do that.
            self.assertEqual(touched, [])

    def test_enter_is_reachable_from_the_cli_with_either_spelling(self) -> None:
        import io

        with tempfile.TemporaryDirectory() as tmp, self.stub_install():
            root = self._project(tmp)
            for argv in (["enter", str(root)], ["enter", "--project", str(root)]):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = project_tool.main(argv)
                self.assertEqual(code, 0)
                payload = json.loads(out.getvalue())
                self.assertEqual(
                    payload["status"]["project_root"], str(root.resolve())
                )


if __name__ == "__main__":
    unittest.main()
