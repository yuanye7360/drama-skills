"""Derived Markdown must not be the only home for its own document metadata.

Re-rendering a derived document used to drop the title prefix and the
creator-facing note, because both arrived as one-off CLI flags and had no
place in the authoritative records. The loss was silent: the renderer
reported success and the note simply stopped existing.

Two mechanisms are asserted here.

1. A leading ``record_kind: "document"`` record carries the document title
   and note, so a bare re-render reproduces them.
2. When ``--out`` already exists, a render that would drop header prose the
   existing document carries is refused, and the file is left untouched.
   This holds even for records that carry no document record at all, so the
   old failure mode cannot recur while the schema is being adopted.
"""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

SUITE = Path(__file__).resolve().parents[1]

SCRIPTS = {
    "image": SUITE / "skills/short-drama-image-prompts/scripts/render_image_prompts.py",
    "sheet": SUITE / "skills/short-drama-storyboard/scripts/render_sheet_prompts.py",
    "keyframe": SUITE
    / "skills/short-drama-storyboard/scripts/render_keyframe_prompts.py",
}


def _load(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(f"_rdm_{name}", SCRIPTS[name])
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULES = {name: _load(name) for name in SCRIPTS}


class DocumentRecordSplitTests(unittest.TestCase):
    """The document record is metadata, never a content record."""

    def test_document_record_is_split_off_and_never_rendered_as_content(self) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                doc, records = module.split_document_record(
                    [
                        {
                            "record_kind": "document",
                            "title": "EP001 · 标题",
                            "note": "覆盖 SC001–SC003。",
                        },
                        {"spec_id": "A"},
                        {"spec_id": "B"},
                    ]
                )
                self.assertEqual(doc["title"], "EP001 · 标题")
                self.assertEqual(doc["note"], "覆盖 SC001–SC003。")
                self.assertEqual([r["spec_id"] for r in records], ["A", "B"])

    def test_absent_document_record_yields_empty_metadata(self) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                doc, records = module.split_document_record([{"spec_id": "A"}])
                self.assertEqual(doc, {})
                self.assertEqual(len(records), 1)

    def test_document_record_must_come_first(self) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                with self.assertRaises(module.RenderError) as caught:
                    module.split_document_record(
                        [{"spec_id": "A"}, {"record_kind": "document", "note": "x"}]
                    )
                self.assertIn("first record", str(caught.exception))

    def test_only_one_document_record_is_allowed(self) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                with self.assertRaises(module.RenderError):
                    module.split_document_record(
                        [
                            {"record_kind": "document", "note": "a"},
                            {"record_kind": "document", "note": "b"},
                        ]
                    )

    def test_unknown_record_kind_is_refused_rather_than_rendered(self) -> None:
        # Silently treating an unknown kind as content is how a metadata typo
        # becomes a garbled panel.
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                with self.assertRaises(module.RenderError) as caught:
                    module.split_document_record([{"record_kind": "documnet"}])
                self.assertIn("record_kind", str(caught.exception))


class HeaderMetadataResolutionTests(unittest.TestCase):
    """Flag beats record, record beats fallback."""

    def test_record_supplies_values_when_no_flag_is_given(self) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                self.assertEqual(
                    module.resolve_header_value(
                        flag=None, document={"note": "从记录来"}, key="note",
                        fallback=None,
                    ),
                    "从记录来",
                )

    def test_flag_overrides_the_record(self) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                self.assertEqual(
                    module.resolve_header_value(
                        flag="从旗标来", document={"note": "从记录来"}, key="note",
                        fallback=None,
                    ),
                    "从旗标来",
                )

    def test_fallback_applies_only_when_both_are_absent(self) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                self.assertEqual(
                    module.resolve_header_value(
                        flag=None, document={}, key="title", fallback="回落标题",
                    ),
                    "回落标题",
                )


class OverwriteGuardTests(unittest.TestCase):
    """An existing derived document may not lose header prose silently."""

    EXISTING = "\n".join(
        [
            "# EP001 · 资产图片提示词",
            "",
            "> 来源：`image-prompt-specs.jsonl`",
            "> 范围：仅提示词，不生成图片或调用媒体服务",
            "",
            "> 覆盖 SC001–SC003（29 镜）。SC004 因地点身份未建档，未出 sheet。",
            "",
            "## `乔凡尼` · `character_sheet`",
            "",
            "正文",
        ]
    )

    def _new(self, *, title: str, note: str | None) -> str:
        lines = [
            "# %s" % title,
            "",
            "> 来源：`image-prompt-specs.jsonl`",
            "> 范围：仅提示词，不生成图片或调用媒体服务",
            "",
        ]
        if note:
            lines += ["> %s" % note, ""]
        lines += ["## `乔凡尼` · `character_sheet`", "", "正文"]
        return "\n".join(lines)

    def test_dropping_the_creator_note_is_refused(self) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                with self.assertRaises(module.RenderError) as caught:
                    module.guard_header_metadata(
                        self.EXISTING,
                        self._new(title="EP001 · 资产图片提示词", note=None),
                        title_explicit=True,
                    )
                message = str(caught.exception)
                self.assertIn("note", message)
                # The message has to name the fix, not just the symptom.
                self.assertIn("record_kind", message)

    def test_losing_the_episode_prefix_is_refused_when_title_is_a_fallback(
        self,
    ) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                with self.assertRaises(module.RenderError) as caught:
                    module.guard_header_metadata(
                        self.EXISTING,
                        self._new(
                            title="资产图片提示词",
                            note="覆盖 SC001–SC003（29 镜）。SC004 因地点身份未建档，未出 sheet。",
                        ),
                        title_explicit=False,
                    )
                self.assertIn("title", str(caught.exception))

    def test_reproducing_the_header_passes(self) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                module.guard_header_metadata(
                    self.EXISTING,
                    self._new(
                        title="EP001 · 资产图片提示词",
                        note="覆盖 SC001–SC003（29 镜）。SC004 因地点身份未建档，未出 sheet。",
                    ),
                    title_explicit=False,
                )

    def test_an_explicit_title_change_is_allowed(self) -> None:
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                module.guard_header_metadata(
                    self.EXISTING,
                    self._new(
                        title="EP001 · 改过的标题",
                        note="覆盖 SC001–SC003（29 镜）。SC004 因地点身份未建档，未出 sheet。",
                    ),
                    title_explicit=True,
                )

    def test_adding_a_note_is_allowed(self) -> None:
        existing = "\n".join(
            [
                "# EP001 · 资产图片提示词",
                "",
                "> 来源：`image-prompt-specs.jsonl`",
                "",
                "## `乔凡尼` · `character_sheet`",
            ]
        )
        for name, module in MODULES.items():
            with self.subTest(renderer=name):
                module.guard_header_metadata(
                    existing,
                    self._new(title="EP001 · 资产图片提示词", note="新加的说明"),
                    title_explicit=False,
                )


class SheetEndToEndTests(unittest.TestCase):
    """A bare re-render of a document-record file reproduces the file."""

    @staticmethod
    def _sheet_record() -> dict[str, Any]:
        return {
            "sheet_id": "SBS-EP001-SC001-A",
            "narrative_group": {"group_id": "A", "title": "教室：被点名"},
            "reference_declarations": [
                {"name": "乔凡尼", "reference_tag": "@[乔凡尼.png]"},
            ],
            "header": {"title_lines": ["EP001 · 标题", "教室 A组"]},
            "grid": {"cols": 3, "rows": 2, "filled": 5, "empty_cells": ["R2C3"]},
            "opening": {"focus": "课堂压力起点", "through_line": "压力持续升级"},
            "previs_style": "黑白铅笔分镜草图：粗略有力线条、强剪影",
            "character_anchors": [
                {
                    "name": "乔凡尼",
                    "tonal_value": "最浅灰",
                    "silhouette_features": ["瘦削肩线"],
                }
            ],
            "global_light": "画左自然光",
            "panels": [
                {
                    "panel_id": "P1",
                    "shot_ref": {"record_id": "SHOT-EP001-SC001-01"},
                    "shot_size": "全景，正面",
                    "camera_movement": "慢推",
                    "action_composition": "老师站画左，教鞭指向星空图",
                    "annotations": {"camera": "慢推向老师"},
                }
            ],
            "element_progression": {"early": "平铺", "mid": "加密", "late": "平铺"},
            "cinematography": ["广角推镜"],
            "environment_keywords": ["黑板", "讲台"],
            "exclusions": ["timestamps", "dialogue"],
        }

    def test_bare_rerender_is_byte_identical(self) -> None:
        module = MODULES["sheet"]
        record = self._sheet_record()
        document = {
            "record_kind": "document",
            "note": "覆盖 SC001。SC004 因地点身份未建档，未出 sheet。",
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sheets = root / "storyboard-sheets.jsonl"
            sheets.write_text(
                "\n".join(
                    json.dumps(r, ensure_ascii=False) for r in (document, record)
                )
                + "\n",
                encoding="utf-8",
            )
            project = root / "short-drama.json"
            project.write_text(
                json.dumps(
                    {
                        "language": "zh",
                        "format": {"prompt_language": "zh", "aspect_ratio": "9:16"},
                    }
                ),
                encoding="utf-8",
            )
            out = root / "storyboard-sheet-prompts.md"
            argv = [str(sheets), "--project", str(project), "--out", str(out)]

            self.assertEqual(module.main(argv), 0)
            first = out.read_text(encoding="utf-8")
            self.assertIn(
                "> 覆盖 SC001。SC004 因地点身份未建档，未出 sheet。", first
            )

            # The second run has to survive its own guard.
            self.assertEqual(module.main(argv), 0)
            self.assertEqual(out.read_text(encoding="utf-8"), first)

    def test_rerender_without_the_document_record_refuses_and_keeps_the_file(
        self,
    ) -> None:
        module = MODULES["sheet"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "storyboard-sheet-prompts.md"
            out.write_text(OverwriteGuardTests.EXISTING, encoding="utf-8")
            sheets = root / "storyboard-sheets.jsonl"
            # A valid content record, but nothing carrying the note the existing
            # document shows: exactly the state that used to delete it.
            sheets.write_text(
                json.dumps(self._sheet_record(), ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            project = root / "short-drama.json"
            project.write_text(
                json.dumps(
                    {
                        "language": "zh",
                        "format": {"prompt_language": "zh", "aspect_ratio": "9:16"},
                    }
                ),
                encoding="utf-8",
            )
            before = out.read_text(encoding="utf-8")
            code = module.main(
                [str(sheets), "--project", str(project), "--out", str(out)]
            )
            self.assertEqual(code, 2)
            self.assertEqual(out.read_text(encoding="utf-8"), before)


class CanonicalPathDerivationTests(unittest.TestCase):
    """A re-render should not need nine hand-assembled path arguments."""

    DERIVERS = dict(MODULES)

    def setUp(self) -> None:
        container_script = (
            SUITE / "skills/short-drama-video-prompts/scripts/render_container_prompts.py"
        )
        spec = importlib.util.spec_from_file_location("_rdm_container", container_script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.container = module

    def test_style_lock_is_found_under_the_canonical_development_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "项目开发").mkdir()
            lock = root / "项目开发" / "style-lock.jsonl"
            lock.write_text("{}\n", encoding="utf-8")
            project = root / "short-drama.json"
            project.write_text("{}", encoding="utf-8")
            for name, module in list(MODULES.items()) + [("container", self.container)]:
                if not hasattr(module, "derive_project_path"):
                    continue
                with self.subTest(renderer=name):
                    self.assertEqual(
                        module.derive_project_path(
                            project, "项目开发", "style-lock.jsonl"
                        ),
                        # The helper resolves, so on macOS the temp dir arrives
                        # as /private/var rather than the /var symlink.
                        lock.resolve(),
                    )

    def test_a_non_canonical_layout_gets_nothing_rather_than_a_wrong_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "short-drama.json"
            project.write_text("{}", encoding="utf-8")
            for name, module in list(MODULES.items()) + [("container", self.container)]:
                if not hasattr(module, "derive_project_path"):
                    continue
                with self.subTest(renderer=name):
                    self.assertIsNone(
                        module.derive_project_path(
                            project, "项目开发", "style-lock.jsonl"
                        )
                    )

    def test_bible_jsonl_files_come_back_sorted(self) -> None:
        module = MODULES["image"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bible = root / "设定集"
            bible.mkdir()
            for name in ("props.jsonl", "characters.jsonl", "locations.jsonl"):
                (bible / name).write_text("{}\n", encoding="utf-8")
            (bible / "notes.md").write_text("ignored", encoding="utf-8")
            project = root / "short-drama.json"
            project.write_text("{}", encoding="utf-8")
            self.assertEqual(
                [p.name for p in module.derive_asset_files(project)],
                ["characters.jsonl", "locations.jsonl", "props.jsonl"],
            )

    def test_missing_style_lock_names_the_flag_to_pass(self) -> None:
        module = MODULES["image"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            specs = root / "image-prompt-specs.jsonl"
            specs.write_text(
                json.dumps({"spec_id": "IMG-1"}, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            project = root / "short-drama.json"
            project.write_text(
                json.dumps({"language": "zh", "format": {"prompt_language": "zh"}}),
                encoding="utf-8",
            )
            self.assertEqual(module.main([str(specs), "--project", str(project)]), 2)


if __name__ == "__main__":
    unittest.main()
