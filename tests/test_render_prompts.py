"""The derived prompt Markdown must be a projection, not a second draft.

These tests pin the two properties that make the rendered file a cache: the
creative text reaches the page verbatim, and any hand edit is detectable.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SUITE = Path(__file__).resolve().parents[1]
SCRIPT = SUITE / "skills/short-drama-storyboard/scripts/render_prompts.py"
SPEC = importlib.util.spec_from_file_location("short_drama_render_prompts", SCRIPT)
assert SPEC and SPEC.loader
render_prompts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(render_prompts)

PROMPT = (
    "近景：她的右手悬在合同上方停住，指尖离纸面两指宽。"
    "合同占据下半画面，签名栏被她的手腕裁去一半。"
    "保持持物与站位不变；排除任何已经翻页或已经握笔的状态。"
)


def shot_record(shot_id: str = "SHOT-012") -> dict[str, object]:
    return {
        "shot_id": shot_id,
        "audience_visibility": [
            {
                "source_ref": {
                    "owner": "short-drama-write",
                    "artifact": "剧集/EP001/screenplay-index.jsonl",
                    "hash": "a" * 64,
                    "record_id": "BLK-07",
                },
                "fact": "合同上的签名是伪造的",
                "permission": "withhold_now",
                "carrier": "none",
                "reveal_trigger": "future",
                "protection_method": "crop+focus",
                "rationale": "本镜只交代她注意到纸角",
            }
        ],
    }


def keyframe_record(
    shot_id: str = "SHOT-012", *, recipe: str = "1.2.0"
) -> dict[str, object]:
    return {
        "keyframe_id": "KEY-012A",
        "status": "accepted",
        "shot_ref": {
            "artifact": "剧集/EP001/storyboard/shots.jsonl",
            "hash": "b" * 64,
            "record_id": shot_id,
            "owner": "short-drama-storyboard",
        },
        "boundary_role": "start",
        "boundary_ref": {
            "artifact": "剧集/EP001/storyboard/shots.jsonl",
            "hash": "b" * 64,
            "record_id": shot_id,
            "field": "/start_boundary",
            "owner": "short-drama-storyboard",
        },
        "purpose": "观众先看见她的手停住，再明白纸上有问题",
        "asset_bindings": [
            {
                "identity_ref": {
                    "owner": "short-drama-assets",
                    "artifact": "设定集/characters.jsonl",
                    "hash": "c" * 64,
                    "record_id": "CHAR-001",
                },
                "variant_ref": {
                    "owner": "short-drama-assets",
                    "artifact": "设定集/character-looks.jsonl",
                    "hash": "d" * 64,
                    "record_id": "LOOK-003",
                },
            }
        ],
        "text_treatment_refs": [
            {
                "owner": "short-drama-assets",
                "artifact": "设定集/props.jsonl",
                "hash": "e" * 64,
                "record_id": "PROP-014",
                "field": "/text_policy",
            }
        ],
        "generic_prompt": PROMPT,
        "derivation": {
            "recipe_version": recipe,
            "input_hashes": ["b" * 64],
            "rendered_hash": "f" * 64,
        },
    }


def sheet_record() -> dict[str, object]:
    def panel(panel_id: str, shot_id: str, note: str) -> dict[str, object]:
        return {
            "panel_id": panel_id,
            "shot_ref": {
                "owner": "short-drama-storyboard",
                "artifact": "剧集/EP001/storyboard/shots.jsonl",
                "hash": "b" * 64,
                "record_id": shot_id,
            },
            "reference_names": ["林越"],
            "shot_size": "中景，略低机位",
            "camera_movement": "固定机位",
            "action_composition": "她的手停在合同上方",
            "dynamic_elements": "指尖颤抖用虚线",
            "environment": "长桌一角",
            "vfx_elements": "无",
            "shot_note": note,
            "annotations": {
                "body_motion": "手向下",
                "camera": "无",
                "composition": "重心偏右",
                "light": "侧后",
                "vfx_energy": "",
            },
        }

    return {
        "sheet_id": "SBS-A1",
        "status": "accepted",
        "narrative_group": {"group_id": "A", "title": "合同室对峙", "story_span": "第一章"},
        "scene_ref": {
            "owner": "short-drama-storyboard",
            "artifact": "剧集/EP001/storyboard/coverage.json",
            "hash": "a" * 64,
            "record_id": "SC001",
        },
        "scene_visual_plan_ref": None,
        "reference_declarations": [
            {
                "name": "林越",
                "asset_ref": {
                    "owner": "short-drama-assets",
                    "artifact": "设定集/characters.jsonl",
                    "hash": "c" * 64,
                    "record_id": "CHAR-001",
                },
                "reference_tag": "@[林越设定板.png]",
            }
        ],
        "header": {"title_lines": ["合同室", "第一次交锋"], "graphics": "分割线", "text_rule": "仅页眉两行"},
        "grid": {
            "cols": 3,
            "rows": 2,
            "filled": 2,
            "empty_cells": [],
            "fill_order": "left-to-right, top-to-bottom",
            "panel_aspect": "9:16",
            "panel_title_format": "SHOT-<id>",
        },
        "opening": {
            "focus": "极端情绪张力",
            "start_at_peak": True,
            "through_line": "她从被压制走到把合同推回桌面",
        },
        "previs_style": "黑白铅笔分镜草图",
        "annotation_legend": {
            "body_motion": "red arrows",
            "camera": "blue arrows",
            "composition": "green marks",
            "light": "orange marks",
            "vfx_energy": "yellow marks",
            "note": "black text",
        },
        "character_anchors": [],
        "panels": [
            panel("PANEL 01", "SHOT-012", "立住犹豫"),
            panel("PANEL 02", "SHOT-013", "转向反击"),
        ],
        "element_progression": {"early": "微妙", "mid": "增强", "late": "收束"},
        "cinematography": ["过肩压缩"],
        "environment_keywords": ["尘光"],
        "geo_map": {"enabled": False, "location_ref": None, "labels": [], "notes": ""},
        "character_sketches": [],
        "exclusions": ["timestamps", "dialogue"],
        "derivation": {
            "recipe_version": "1.1.0",
            "input_hashes": ["b" * 64],
            "rendered_hash": "f" * 64,
        },
    }


def write_jsonl(path: Path, records: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


class RenderPromptsTests(unittest.TestCase):
    def render_keyframes(self, **overrides: object) -> str:
        keyframes = [overrides.get("keyframe", keyframe_record())]
        shots = [overrides.get("shot", shot_record())]
        return render_prompts.render_keyframes(
            keyframes, shots, episode="EP001", source_hash="0" * 64
        )

    def test_creative_text_reaches_the_page_verbatim(self) -> None:
        """The whole point: the prompt is projected, never re-written."""

        document = self.render_keyframes()

        self.assertIn(f"> {PROMPT}", document)
        self.assertIn("## `SHOT-012` · `KEY-012A`", document)
        self.assertIn("- **镜头目的**：观众先看见她的手停住，再明白纸上有问题", document)
        self.assertIn("- **资产绑定**：CHAR-001+LOOK-003", document)
        self.assertIn("- **文字处理**：PROP-014/text_policy", document)
        self.assertIn(f"- **边界来源**：`SHOT-012/start_boundary` @ `{'b' * 64}`", document)

    def test_audience_visibility_comes_from_the_owning_shot(self) -> None:
        document = self.render_keyframes()

        self.assertIn(
            "- **观众可见性**：合同上的签名是伪造的 · withhold_now · none · future · crop+focus",
            document,
        )

    def test_rendering_is_deterministic(self) -> None:
        self.assertEqual(self.render_keyframes(), self.render_keyframes())

    def test_body_hash_ignores_the_header_but_tracks_the_body(self) -> None:
        """The header carries the digest, so it cannot be inside the digest."""

        document = self.render_keyframes()
        edited_header = document.replace("EP001 · 冻结关键帧", "EP002 · 冻结关键帧")
        edited_body = document.replace("观众先看见", "观众先看到")

        self.assertEqual(
            render_prompts.body_hash(document), render_prompts.body_hash(edited_header)
        )
        self.assertNotEqual(
            render_prompts.body_hash(document), render_prompts.body_hash(edited_body)
        )

    def test_a_keyframe_without_its_shot_is_refused(self) -> None:
        with self.assertRaisesRegex(render_prompts.RenderError, "unknown shot"):
            self.render_keyframes(shot=shot_record("SHOT-999"))

    def test_a_missing_required_field_is_refused_not_blanked(self) -> None:
        incomplete = keyframe_record()
        del incomplete["generic_prompt"]

        with self.assertRaisesRegex(render_prompts.RenderError, "generic_prompt"):
            self.render_keyframes(keyframe=incomplete)

    def test_mixed_recipe_versions_are_refused(self) -> None:
        with self.assertRaisesRegex(render_prompts.RenderError, "recipe_version"):
            render_prompts.render_keyframes(
                [keyframe_record(), keyframe_record(recipe="9.9.9")],
                [shot_record()],
                episode="EP001",
                source_hash="0" * 64,
            )

    def test_sheet_panels_keep_their_order_and_shot_mapping(self) -> None:
        document = render_prompts.render_sheets(
            [sheet_record()], episode="EP001", source_hash="0" * 64
        )

        self.assertIn(
            "- **格↔镜头**：PANEL 01→SHOT-012 · PANEL 02→SHOT-013（一格一镜，格顺序=叙事先后）",
            document,
        )
        self.assertLess(document.index("PANEL 01"), document.index("PANEL 02"))
        self.assertIn("> 镜头笔记：立住犹豫", document)
        self.assertIn("- **视觉计划**：无", document)
        # An empty annotation channel is dropped rather than printed as a blank.
        self.assertIn("> 标注：红色箭头-手向下；蓝色箭头-无；绿色标记-重心偏右；橙色标记-侧后", document)

    def test_check_mode_accepts_a_current_file_and_rejects_a_hand_edit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            keyframes = write_jsonl(root / "keyframes.jsonl", [keyframe_record()])
            shots = write_jsonl(root / "shots.jsonl", [shot_record()])
            rendered = root / "keyframe-prompts.md"
            arguments = [
                sys.executable,
                str(SCRIPT),
                "keyframes",
                str(keyframes),
                "--shots",
                str(shots),
                "--episode",
                "EP001",
            ]
            subprocess.run(
                [*arguments, "--out", str(rendered)], check=True, capture_output=True
            )

            current = subprocess.run(
                [*arguments, "--check", str(rendered)], capture_output=True, text=True
            )
            rendered.write_text(
                rendered.read_text(encoding="utf-8").replace("停住", "松开"),
                encoding="utf-8",
            )
            drifted = subprocess.run(
                [*arguments, "--check", str(rendered)], capture_output=True, text=True
            )

            self.assertEqual(current.returncode, 0)
            self.assertEqual(drifted.returncode, 1)
            self.assertEqual(json.loads(drifted.stdout)["status"], "stale")

    def test_cli_reports_a_bad_record_instead_of_writing_a_broken_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            incomplete = keyframe_record()
            del incomplete["purpose"]
            keyframes = write_jsonl(root / "keyframes.jsonl", [incomplete])
            shots = write_jsonl(root / "shots.jsonl", [shot_record()])
            out = root / "keyframe-prompts.md"

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "keyframes",
                    str(keyframes),
                    "--shots",
                    str(shots),
                    "--episode",
                    "EP001",
                    "--out",
                    str(out),
                ],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 2)
            self.assertIn("purpose", result.stderr)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
