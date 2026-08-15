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


VIDEO_SCRIPT = SUITE / "skills/short-drama-video-prompts/scripts/render_prompts.py"
VIDEO_SPEC = importlib.util.spec_from_file_location(
    "short_drama_render_video_prompts", VIDEO_SCRIPT
)
assert VIDEO_SPEC and VIDEO_SPEC.loader
render_video = importlib.util.module_from_spec(VIDEO_SPEC)
VIDEO_SPEC.loader.exec_module(render_video)

MOTION_PROMPT = (
    "从她的手悬在合同上方开始。手指先收紧，再整只手离开纸面；她抬眼对上对方。"
    "摄影机固定，不移动。在 3.5 秒内让犹豫—决定—开口各占一段。"
)


def motion_shot() -> dict[str, object]:
    return {"shot_id": "SHOT-012", "purpose": "让观众先看见她的犹豫，再看见她改变主意"}


def motion_record() -> dict[str, object]:
    return {
        "motion_id": "MOTION-012",
        "status": "accepted",
        "shot_ref": {
            "artifact": "剧集/EP001/storyboard/shots.jsonl",
            "hash": "b" * 64,
            "record_id": "SHOT-012",
            "owner": "short-drama-storyboard",
        },
        "keyframe_ref": {
            "artifact": "剧集/EP001/storyboard/keyframes.jsonl",
            "hash": "a" * 64,
            "record_id": "KEY-012A",
            "owner": "short-drama-storyboard",
        },
        "boundary_refs": {
            "duration": {
                "artifact": "剧集/EP001/storyboard/shots.jsonl",
                "hash": "b" * 64,
                "record_id": "SHOT-012",
                "field": "/duration_seconds",
                "value_seconds": 3.5,
                "owner": "short-drama-storyboard",
            },
            "next_start": {
                "artifact": "剧集/EP001/storyboard/shots.jsonl",
                "hash": "b" * 64,
                "record_id": "SHOT-013",
                "field": "/start_boundary",
                "access": "comparison_only",
                "owner": "short-drama-storyboard",
            },
        },
        "reference_bindings": [
            {
                "slot_id": "REF-1",
                "order": 1,
                "artifact_ref": {
                    "owner": "short-drama-storyboard",
                    "artifact": "剧集/EP001/storyboard/keyframes.jsonl",
                    "hash": "a" * 64,
                    "record_id": "KEY-012A",
                },
                "role": "start_frame",
                "may_control": ["起始构图"],
                "must_not_control": ["终态"],
                "admission_status": "unverified",
                "reference_observation_ref": None,
                "unresolved_risks": ["水印"],
            }
        ],
        "audio": [
            {
                "source_ref": {
                    "artifact": "剧集/EP001/screenplay-index.jsonl",
                    "hash": "c" * 64,
                    "owner": "short-drama-write",
                    "record_id": "BLK-EP001-SC01-D03",
                },
                "kind": "dialogue",
                "exact_text": "这不是我签的。",
                "delivery_or_spatial_intent": "压低",
                "timing": "后半段",
            }
        ],
        "end_report": {
            "projection": {
                "pose": "直立",
                "position": "桌前",
                "gaze": "对视",
                "hands": "右手离纸",
                "held_props": "无",
                "visible_state": "合同被推回",
            },
            "comparison": "match",
            "source_end_hash": "b" * 64,
            "differences": [],
        },
        "creator_overrides": [],
        "generic_prompt": MOTION_PROMPT,
        "derivation": {
            "recipe_version": "2.0.1",
            "input_hashes": ["b" * 64],
            "rendered_hash": "f" * 64,
        },
    }


class RenderVideoPromptsTests(unittest.TestCase):
    def render(self, motion: dict[str, object] | None = None) -> str:
        return render_video.render_motions(
            [motion or motion_record()],
            [motion_shot()],
            episode="EP001",
            source_hash="0" * 64,
        )

    def test_prompt_and_read_only_facts_are_projected_verbatim(self) -> None:
        document = self.render()

        self.assertIn(f"> {MOTION_PROMPT}", document)
        self.assertIn("## `SHOT-012` · 让观众先看见她的犹豫，再看见她改变主意", document)
        self.assertIn("- **时长（只读）**：`3.5s`", document)
        self.assertIn("- **边界核对**：`end match`", document)
        self.assertIn("- **声音引用**：dialogue:BLK-EP001-SC01-D03", document)
        self.assertIn("- **下一镜**：仅比较 `SHOT-013`，未改写", document)

    def test_a_plain_master_omits_the_coverage_line(self) -> None:
        """`普通母版省略"覆盖范围"一行` — no `master` placeholder bookkeeping."""

        self.assertNotIn("覆盖范围", self.render())

    def test_a_pickup_declares_its_coverage_scope(self) -> None:
        pickup = motion_record()
        pickup["coverage_scope"] = {
            "mode": "pickup",
            "master_motion_id": "MOTION-012",
            "supplements_motion_ids": [],
            "source_obligations": [
                {
                    "kind": "reaction",
                    "source_ref": {"record_id": "BLK-EP001-SC01-R02"},
                    "disposition": "covered_now",
                    "motion_field": "/ordered_subject_motion",
                }
            ],
            "replacement_intent": "does_not_replace_master",
        }

        document = self.render(pickup)

        self.assertIn("- **覆盖范围（仅补拍/替代版）**：`pickup`", document)
        self.assertIn("BLK-EP001-SC01-R02 → /ordered_subject_motion/covered_now", document)

    def test_a_motion_without_its_shot_is_refused(self) -> None:
        orphan = motion_record()
        orphan["shot_ref"] = {"record_id": "SHOT-999", "hash": "b" * 64}

        with self.assertRaisesRegex(render_video.RenderError, "unknown shot"):
            self.render(orphan)

    def test_a_missing_duration_is_refused_not_guessed(self) -> None:
        undated = motion_record()
        boundaries = undated["boundary_refs"]
        assert isinstance(boundaries, dict)
        del boundaries["duration"]["value_seconds"]  # type: ignore[index]

        with self.assertRaisesRegex(render_video.RenderError, "value_seconds"):
            self.render(undated)

    def test_containers_project_member_order_and_duration(self) -> None:
        container = {
            "container_id": "CONT-01",
            "status": "accepted",
            "members": [
                {
                    "order": 2,
                    "shot_ref": {"record_id": "SHOT-013", "hash": "b" * 64},
                    "motion_ref": {"record_id": "MOTION-013"},
                    "accepted_duration": 2.0,
                },
                {
                    "order": 1,
                    "shot_ref": {"record_id": "SHOT-012", "hash": "b" * 64},
                    "motion_ref": {"record_id": "MOTION-012"},
                    "accepted_duration": 3.5,
                },
            ],
            "container_duration": 5.5,
        }

        document = render_video.render_containers(
            [container], episode="EP001", source_hash="0" * 64
        )

        # Declared order wins over file order; the renderer never re-sequences
        # by position in the file.
        self.assertIn("## 容器 `CONT-01` · 成员 `SHOT-012,SHOT-013` · 5.5s", document)
        self.assertLess(document.index("SHOT-012 @"), document.index("SHOT-013 @"))

    def test_check_mode_detects_a_hand_edited_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            motions = write_jsonl(root / "motion-specs.jsonl", [motion_record()])
            shots = write_jsonl(root / "shots.jsonl", [motion_shot()])
            rendered = root / "video-prompts.md"
            arguments = [
                sys.executable,
                str(VIDEO_SCRIPT),
                "motions",
                str(motions),
                "--shots",
                str(shots),
                "--episode",
                "EP001",
            ]
            subprocess.run(
                [*arguments, "--out", str(rendered)], check=True, capture_output=True
            )
            rendered.write_text(
                rendered.read_text(encoding="utf-8").replace("摄影机固定", "摄影机缓推"),
                encoding="utf-8",
            )

            drifted = subprocess.run(
                [*arguments, "--check", str(rendered)], capture_output=True, text=True
            )

            self.assertEqual(drifted.returncode, 1)
            self.assertEqual(json.loads(drifted.stdout)["status"], "stale")


IMAGE_SCRIPT = SUITE / "skills/short-drama-image-prompts/scripts/render_prompts.py"
IMAGE_SPEC = importlib.util.spec_from_file_location(
    "short_drama_render_image_prompts", IMAGE_SCRIPT
)
assert IMAGE_SPEC and IMAGE_SPEC.loader
render_image = importlib.util.module_from_spec(IMAGE_SPEC)
IMAGE_SPEC.loader.exec_module(render_image)

IMAGE_PROMPT = (
    "写实都市剧风格锁。三视图人物参考：二十八岁女性，左颊有一道浅疤，"
    "深灰西装外套袖口磨白。中性灰背景，均匀布光。保持疤痕位置与袖口磨损；排除任何配饰。"
)


def image_spec(*, with_edit: bool = False) -> dict[str, object]:
    spec: dict[str, object] = {
        "spec_id": "IMG-001",
        "status": "accepted",
        "purpose": "character_sheet",
        "asset_binding": {
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
        },
        "intent": {"reuse_job": "全剧人物身份基准", "audience": "分镜与视频阶段"},
        "reference_bindings": [],
        "text_handling": {
            "source_policy_ref": {
                "artifact": "设定集/props.jsonl",
                "hash": "e" * 64,
                "field": "/text_policy",
                "owner": "short-drama-assets",
                "record_id": "PROP-014",
            },
            "source_mode": "no_readable_text",
            "render_treatment": {"mode": "blank"},
        },
        "creator_overrides": [],
        "generic_prompt": IMAGE_PROMPT,
        "recipe": {"name": "character-sheet", "version": "1.4.0", "hash": "a" * 64},
        "derivation": {
            "input_hashes": ["c" * 64],
            "renderer": "generic-markdown",
            "rendered_hash": "f" * 64,
        },
        "provenance": "creator_project",
    }
    if with_edit:
        spec["edit"] = {
            "changes": ["左袖口新增血迹"],
            "preserve": ["面部", "疤痕位置", "构图"],
            "continuity_impact": "PSTATE-007",
            "target_ref": {
                "owner": "short-drama-image-prompts",
                "artifact": "设定集/image-prompt-specs.jsonl",
                "hash": "b" * 64,
                "record_id": "IMG-001",
                "field": "/generic_prompt",
            },
            "entity_or_region": "左袖口",
        }
    return spec


class RenderImagePromptsTests(unittest.TestCase):
    def test_prompt_and_bindings_are_projected_verbatim(self) -> None:
        document = render_image.render_specs(
            [image_spec()], episode="EP001", source_hash="0" * 64
        )

        self.assertIn(f"> {IMAGE_PROMPT}", document)
        self.assertIn("## `CHAR-001` · `character_sheet`", document)
        self.assertIn("- **规格**：`IMG-001`", document)
        self.assertIn("- **绑定**：`CHAR-001` + `LOOK-003`", document)
        self.assertIn("- **用途**：全剧人物身份基准", document)
        self.assertIn("- **文字来源政策**：`no_readable_text`", document)
        self.assertIn("- **参考图用途**：无", document)
        self.assertIn("> 配方：`character-sheet@1.4.0`", document)

    def test_a_plain_sheet_omits_the_edit_section(self) -> None:
        """`非变体可省略` — no empty variant bookkeeping on a base plate."""

        document = render_image.render_specs(
            [image_spec()], episode="EP001", source_hash="0" * 64
        )

        self.assertNotIn("变体/编辑说明", document)

    def test_an_edit_declares_its_preserve_set(self) -> None:
        document = render_image.render_specs(
            [image_spec(with_edit=True)], episode="EP001", source_hash="0" * 64
        )

        self.assertIn("### 变体/编辑说明", document)
        self.assertIn("- **变化**：左袖口新增血迹", document)
        self.assertIn("- **必须保持**：面部 / 疤痕位置 / 构图", document)
        self.assertIn("- **连续性影响**：PSTATE-007", document)

    def test_a_missing_prompt_is_refused_not_blanked(self) -> None:
        incomplete = image_spec()
        del incomplete["generic_prompt"]

        with self.assertRaisesRegex(render_image.RenderError, "generic_prompt"):
            render_image.render_specs(
                [incomplete], episode="EP001", source_hash="0" * 64
            )

    def test_mixed_recipes_are_refused(self) -> None:
        other = image_spec()
        other["spec_id"] = "IMG-002"
        other["recipe"] = {"name": "prop-plate", "version": "9.9.9", "hash": "a" * 64}

        with self.assertRaisesRegex(render_image.RenderError, "one recipe"):
            render_image.render_specs(
                [image_spec(), other], episode="EP001", source_hash="0" * 64
            )

    def test_check_mode_detects_a_hand_edited_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            specs = write_jsonl(root / "image-prompt-specs.jsonl", [image_spec()])
            rendered = root / "image-prompts.md"
            arguments = [
                sys.executable,
                str(IMAGE_SCRIPT),
                str(specs),
                "--episode",
                "EP001",
            ]
            subprocess.run(
                [*arguments, "--out", str(rendered)], check=True, capture_output=True
            )
            rendered.write_text(
                rendered.read_text(encoding="utf-8").replace("中性灰背景", "纯白背景"),
                encoding="utf-8",
            )

            drifted = subprocess.run(
                [*arguments, "--check", str(rendered)], capture_output=True, text=True
            )

            self.assertEqual(drifted.returncode, 1)
            self.assertEqual(json.loads(drifted.stdout)["status"], "stale")


if __name__ == "__main__":
    unittest.main()
