import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

SUITE = Path(__file__).resolve().parents[1]
SCRIPT = SUITE / "skills/short-drama-storyboard/scripts/render_sheet_prompts.py"
SPEC = importlib.util.spec_from_file_location("render_sheet_prompts", SCRIPT)
assert SPEC and SPEC.loader
render_sheet_prompts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_sheet_prompts)


def sheet(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
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
                "annotations": {"camera": "慢推向老师", "composition": "三段式"},
            }
        ],
        "element_progression": {"early": "平铺", "mid": "略加密", "late": "回归平铺"},
        "cinematography": ["广角推镜"],
        "environment_keywords": ["黑板", "讲台"],
        "exclusions": ["timestamps", "dialogue"],
    }
    record.update(overrides)
    return record


def project(language: str = "zh", prompt_language: str = "zh") -> dict[str, Any]:
    return {
        "language": language,
        "format": {"prompt_language": prompt_language, "aspect_ratio": "9:16"},
    }


class RenderShapeTests(unittest.TestCase):
    def render(self, record: dict[str, Any]) -> str:
        return render_sheet_prompts.render(
            [record],
            episode_id="EP001",
            aspect_ratio="9:16",
            prompt_language="zh",
            note=None,
        )

    def test_copyable_body_sits_in_a_fence_not_a_blockquote(self) -> None:
        # A sheet body runs to dozens of lines. Inside a blockquote every one of
        # them copies out carrying a "> " prefix, which is the opposite of what
        # "可复制" promises; keyframe's single short paragraph is the only case
        # a blockquote suits.
        text = self.render(sheet())
        self.assertIn("```text", text)
        body = text.split("```text", 1)[1].split("```", 1)[0]
        self.assertNotIn("\n> ", body)

    def test_inapplicable_fields_are_omitted_rather_than_filled(self) -> None:
        # A rendered 「无」 reads to an image model as something to draw, and to a
        # creator as noise across every panel.
        record = sheet()
        record["panels"][0].update(
            {
                "camera_movement": "固定机位",
                "dynamic_elements": "无",
                "vfx_elements": "无（此格纯反应定格）",
                "environment": "   ",
            }
        )
        text = self.render(record)
        panel = [l for l in text.splitlines() if l.startswith("PANEL 01")][0]
        self.assertNotIn("固定机位", panel)
        self.assertNotIn("无", text.split("面板进展：", 1)[1].split("元素进展", 1)[0])

    def test_a_fixed_camera_note_that_carries_information_survives(self) -> None:
        record = sheet()
        record["panels"][0]["camera_movement"] = "固定机位，高俯角"
        self.assertIn("固定机位，高俯角", self.render(record))

    def test_panel_annotations_list_only_the_arrows_that_panel_carries(self) -> None:
        # The five-colour legend is stated once globally; restating it per panel
        # multiplies it by the panel count and is mostly "-无" and "-固定".
        record = sheet()
        record["panels"][0]["annotations"] = {
            "body_motion": "无",
            "camera": "慢推向老师",
            "vfx_energy": "",
        }
        text = self.render(record)
        annotation = [l for l in text.splitlines() if l.startswith("标注：")][0]
        self.assertEqual(annotation, "标注：蓝-慢推向老师")

    def test_recognition_anchors_precede_the_panels(self) -> None:
        # A panel cannot be read before the reader knows who is who.
        text = self.render(sheet())
        self.assertLess(text.index("角色靠固定灰度"), text.index("面板进展："))

    def test_exclusions_render_as_sentences_from_machine_keys(self) -> None:
        text = self.render(sheet())
        self.assertIn("无时间戳。无对白文字。", text)
        self.assertNotIn("timestamps", text)

    def test_an_unknown_exclusion_key_is_refused_not_pasted_through(self) -> None:
        # Storing prompt literals in `exclusions` is how a mixed Chinese/English
        # comma blob reached a rendered prompt once already.
        record = sheet(exclusions=["timestamps", "无水印、logos/watermarks"])
        with self.assertRaises(render_sheet_prompts.RenderError):
            self.render(record)

    def test_a_panel_with_no_composition_prose_is_refused(self) -> None:
        record = sheet()
        record["panels"][0]["action_composition"] = "无"
        with self.assertRaises(render_sheet_prompts.RenderError):
            self.render(record)

    def test_the_panel_ratio_comes_from_the_grid_not_the_delivery_ratio(self) -> None:
        # A 4x2 grid of 9:16 panels is not a 9:16 sheet, and the header band
        # takes space no derivation knows about, so the paper ratio is stated
        # only when the creator chose one.
        record = sheet()
        record["grid"]["panel_aspect"] = "9:16，单格取景统一"
        text = self.render(record)
        self.assertIn("每格取景比例 9:16，单格取景统一", text)
        self.assertNotIn("9:16 故事板纸张", text)

    def test_a_chosen_paper_ratio_is_stated(self) -> None:
        record = sheet()
        record["grid"]["sheet_aspect"] = "4:3"
        self.assertIn("4:3 故事板纸张", self.render(record))

    def test_rendering_is_deterministic(self) -> None:
        self.assertEqual(self.render(sheet()), self.render(sheet()))


class LanguageContractTests(unittest.TestCase):
    def run_cli(self, proj: dict[str, Any]) -> int:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sheets = root / "storyboard-sheets.jsonl"
            sheets.write_text(
                json.dumps(sheet(), ensure_ascii=False) + "\n", encoding="utf-8"
            )
            config = root / "short-drama.json"
            config.write_text(json.dumps(proj, ensure_ascii=False), encoding="utf-8")
            return render_sheet_prompts.main(
                [str(sheets), "--project", str(config), "--out", str(root / "o.md")]
            )

    def test_matching_languages_render(self) -> None:
        self.assertEqual(self.run_cli(project("zh", "zh")), 0)

    def test_a_language_mismatch_is_refused_rather_than_rendered(self) -> None:
        # Assembly reuses the record's prose verbatim. Emitting it under a
        # different prompt_language would ship confident text in the wrong
        # language — exactly the drift the two-field contract exists to prevent.
        self.assertEqual(self.run_cli(project("zh", "en")), 2)

    def test_a_missing_prompt_language_falls_back_to_the_documented_default(
        self,
    ) -> None:
        proj = project("zh", "zh")
        del proj["format"]["prompt_language"]
        self.assertEqual(self.run_cli(proj), 2)


if __name__ == "__main__":
    unittest.main()
