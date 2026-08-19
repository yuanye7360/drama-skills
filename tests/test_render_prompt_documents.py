import importlib.util
import unittest
from pathlib import Path
from typing import Any

SUITE = Path(__file__).resolve().parents[1]


def _load(relative: str, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, SUITE / relative)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


keyframe_renderer = _load(
    "skills/short-drama-storyboard/scripts/render_keyframe_prompts.py",
    "render_keyframe_prompts",
)
container_renderer = _load(
    "skills/short-drama-video-prompts/scripts/render_container_prompts.py",
    "render_container_prompts",
)


def shot(shot_id: str, *, chars: list[str], location: str, duration: float = 2.0) -> dict:
    return {
        "shot_id": shot_id,
        "duration_seconds": duration,
        "location_binding": {"identity_ref": {"record_id": location}},
        "asset_bindings": [
            {"identity_ref": {"record_id": c}, "variant_ref": {"record_id": c + "-DAILY"}}
            for c in chars
        ],
        "audience_visibility": [],
    }


def keyframe(shot_id: str, **overrides: Any) -> dict:
    record: dict[str, Any] = {
        "keyframe_id": shot_id.replace("SHOT-", "KEY-") + "-START",
        "shot_ref": {"record_id": shot_id},
        "boundary_role": "start",
        "boundary_ref": {"record_id": shot_id, "hash": "a" * 64, "field": "/start_boundary"},
        "purpose": "建立场域",
        "asset_bindings": [
            {
                "identity_ref": {"record_id": "CHAR-A"},
                "variant_ref": {"record_id": "LOOK-A"},
            }
        ],
        "text_treatment_refs": [],
        "generic_prompt": "教室内景全景。教师站在黑板旁。",
    }
    record.update(overrides)
    return record


class KeyframeRendererTests(unittest.TestCase):
    def render(self, keyframes: list[dict], shots: dict[str, dict]) -> str:
        return keyframe_renderer.render(
            keyframes, shots, episode_id="EP001", prompt_language="zh", note=None
        )

    def test_place_comes_from_the_shot_not_the_keyframe(self) -> None:
        # A keyframe binds the figures it freezes; the shot owns where it
        # happens. Reading the location off the keyframe finds nothing and
        # silently ships a prompt with no place in it.
        shots = {"SHOT-1": shot("SHOT-1", chars=["CHAR-A"], location="LOC-CLASSROOM")}
        text = self.render([keyframe("SHOT-1")], shots)
        self.assertIn("地点 LOC-CLASSROOM", text)
        self.assertIn("人物/道具 CHAR-A/LOOK-A", text)

    def test_a_short_body_stays_a_blockquote(self) -> None:
        # The sheet body needs a fence because it runs to dozens of lines; a
        # one-paragraph keyframe body does not, and switching between the two
        # shapes between renders is the drift this script removes.
        text = self.render([keyframe("SHOT-1")], {"SHOT-1": shot("SHOT-1", chars=[], location="L")})
        self.assertIn("\n> 教室内景全景。", text)
        self.assertNotIn("```", text)

    def test_a_multi_paragraph_body_is_refused(self) -> None:
        # A keyframe freezes one instant; a body needing paragraphs is a motion
        # description wearing a keyframe's name.
        record = keyframe("SHOT-1", generic_prompt="第一段。\n\n第二段。")
        with self.assertRaises(keyframe_renderer.RenderError):
            self.render([record], {"SHOT-1": shot("SHOT-1", chars=[], location="L")})

    def test_boundary_role_must_match_the_bound_field(self) -> None:
        record = keyframe(
            "SHOT-1",
            boundary_role="start",
            boundary_ref={"record_id": "SHOT-1", "hash": "b" * 64, "field": "/end_boundary"},
        )
        with self.assertRaises(keyframe_renderer.RenderError):
            self.render([record], {"SHOT-1": shot("SHOT-1", chars=[], location="L")})

    def test_two_keyframes_on_the_same_end_are_refused(self) -> None:
        shots = {"SHOT-1": shot("SHOT-1", chars=[], location="L")}
        with self.assertRaises(keyframe_renderer.RenderError):
            self.render([keyframe("SHOT-1"), keyframe("SHOT-1")], shots)

    def test_an_empty_text_policy_is_omitted_not_narrated(self) -> None:
        # Only an accepted policy may appear; with no refs there is nothing to
        # show, and a derived sentence would put un-sourced prose where the
        # contract requires a pointer.
        text = self.render([keyframe("SHOT-1")], {"SHOT-1": shot("SHOT-1", chars=[], location="L")})
        self.assertNotIn("文字处理", text)


def member(order: int, shot_id: str, duration: float) -> dict:
    return {
        "order": order,
        "shot_ref": {"record_id": shot_id},
        "accepted_duration": duration,
    }


def container(cid: str, members: list[dict], seam: dict, sheet_id: str = "SBS-A") -> dict:
    return {
        "container_id": cid,
        "storyboard_sheet_ref": {"record_id": sheet_id},
        "first_frame_ref": {"record_id": "KEY-1-START"},
        "members": members,
        "container_duration": sum(m["accepted_duration"] for m in members),
        "seam": seam,
    }


def sheet(shot_ids: list[str]) -> dict:
    return {
        "sheet_id": "SBS-A",
        "reference_declarations": [{"name": "甲", "reference_tag": "@[甲.png]"}],
        "panels": [
            {"shot_ref": {"record_id": s}, "reference_names": ["甲"]} for s in shot_ids
        ],
        "environment_keywords": ["黑板"],
        "element_progression": {"early": "平铺", "mid": "加密", "late": "回落"},
        "global_light": "画左自然光",
    }


class ContainerRendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.shots = {
            "SHOT-EP001-SC001-01": shot(
                "SHOT-EP001-SC001-01", chars=["CHAR-A"], location="LOC-ROOM"
            ),
            "SHOT-EP001-SC001-02": shot(
                "SHOT-EP001-SC001-02", chars=["CHAR-A"], location="LOC-ROOM"
            ),
            "SHOT-EP001-SC002-01": shot(
                "SHOT-EP001-SC002-01", chars=["CHAR-B"], location="LOC-STREET"
            ),
        }
        self.motions = {k: "起点：甲站着。终点：甲坐下。" for k in self.shots}
        self.sheets = {"SBS-A": sheet(list(self.shots))}

    def render(self, containers: list[dict]) -> str:
        return container_renderer.render(
            containers,
            self.shots,
            self.motions,
            self.sheets,
            style_lock="二维有限动画画风。",
            prompt_language="zh",
        )

    def test_segments_are_offset_from_accepted_durations(self) -> None:
        text = self.render(
            [
                container(
                    "CONT-1",
                    [member(1, "SHOT-EP001-SC001-01", 3.5), member(2, "SHOT-EP001-SC001-02", 1.5)],
                    {"kind": "episode_end"},
                )
            ]
        )
        self.assertIn("[SC001-01 | 0.0–3.5s]", text)
        self.assertIn("[SC001-02 | 3.5–5.0s]", text)

    def test_container_duration_must_equal_the_member_sum(self) -> None:
        record = container(
            "CONT-1", [member(1, "SHOT-EP001-SC001-01", 3.5)], {"kind": "episode_end"}
        )
        record["container_duration"] = 9.0
        with self.assertRaises(container_renderer.RenderError):
            self.render([record])

    def test_a_shot_cannot_be_claimed_by_two_containers(self) -> None:
        # One shot in two containers inflates the episode by a whole segment,
        # and neither container looks wrong on its own.
        one = container(
            "CONT-1", [member(1, "SHOT-EP001-SC001-01", 2.0)], {"kind": "episode_end"}
        )
        two = container(
            "CONT-2", [member(1, "SHOT-EP001-SC001-01", 2.0)], {"kind": "episode_end"}
        )
        with self.assertRaises(container_renderer.RenderError):
            self.render([one, two])

    def test_a_match_cut_claim_across_a_subject_change_is_refused(self) -> None:
        # This is the failure VID-21 originally invited: the seam is worded as a
        # shared frame, so the generator is asked for the incoming subject at the
        # outgoing segment's end.
        record = container(
            "CONT-1",
            [member(1, "SHOT-EP001-SC001-01", 2.0)],
            {
                "kind": "match_cut",
                "shared_frame": True,
                "tail_shot_ref": {"record_id": "SHOT-EP001-SC001-01"},
                "head_shot_ref": {"record_id": "SHOT-EP001-SC002-01"},
                "head_frame_ref": {"record_id": "KEY-X"},
            },
        )
        with self.assertRaises(container_renderer.RenderError):
            self.render([record])

    def test_a_hard_cut_says_the_two_frames_are_not_shared(self) -> None:
        record = container(
            "CONT-1",
            [member(1, "SHOT-EP001-SC001-01", 2.0)],
            {
                "kind": "hard_cut",
                "shared_frame": False,
                "tail_shot_ref": {"record_id": "SHOT-EP001-SC001-01"},
                "head_shot_ref": {"record_id": "SHOT-EP001-SC002-01"},
                "head_frame_ref": {"record_id": "KEY-X"},
            },
        )
        text = self.render([record])
        self.assertIn("不共享帧", text)

    def test_a_genuine_match_cut_renders_the_shared_frame(self) -> None:
        record = container(
            "CONT-1",
            [member(1, "SHOT-EP001-SC001-01", 2.0)],
            {
                "kind": "match_cut",
                "shared_frame": True,
                "tail_shot_ref": {"record_id": "SHOT-EP001-SC001-01"},
                "head_shot_ref": {"record_id": "SHOT-EP001-SC001-02"},
                "head_frame_ref": {"record_id": "KEY-NEXT"},
            },
        )
        text = self.render([record])
        self.assertIn("可共享接缝帧：`KEY-NEXT`", text)

    def test_classify_seam_needs_one_subject_carried_across_one_place(self) -> None:
        same = self.shots["SHOT-EP001-SC001-01"]
        other_place = self.shots["SHOT-EP001-SC002-01"]
        self.assertEqual(
            container_renderer.classify_seam(same, self.shots["SHOT-EP001-SC001-02"]),
            "match_cut",
        )
        self.assertEqual(container_renderer.classify_seam(same, other_place), "hard_cut")

    def test_every_container_carries_the_exclusions(self) -> None:
        # Dropping this line is invisible in the record and in the document's
        # shape, and a generator with no exclusions will burn in subtitles, a
        # watermark or a logo. It shipped once already.
        text = self.render(
            [
                container(
                    "CONT-1",
                    [member(1, "SHOT-EP001-SC001-01", 2.0)],
                    {"kind": "episode_end"},
                )
            ]
        )
        self.assertIn("无字幕", text)
        self.assertIn("无水印", text)

    def test_references_cover_only_the_panels_this_container_holds(self) -> None:
        text = self.render(
            [
                container(
                    "CONT-1",
                    [member(1, "SHOT-EP001-SC001-01", 2.0)],
                    {"kind": "episode_end"},
                )
            ]
        )
        self.assertIn("@[甲.png]", text)
        self.assertIn("角色与场景设计参考", text)


if __name__ == "__main__":
    unittest.main()


image_renderer = _load(
    "skills/short-drama-image-prompts/scripts/render_image_prompts.py",
    "render_image_prompts",
)


def asset_spec(**overrides: Any) -> dict:
    record: dict[str, Any] = {
        "spec_id": "IMG-A-001",
        "purpose": "character_sheet",
        "asset_binding": {
            "identity_ref": {"record_id": "CHAR-A"},
            "variant_ref": {"record_id": "LOOK-A"},
        },
        "intent": {"reuse_job": "跨集保持身份", "audience": "分镜阶段"},
        "reference_bindings": [],
        "constraints": [],
        "variant_deltas": [],
        "generic_prompt": "二维有限动画画风。角色设定板，三视图。",
    }
    record.update(overrides)
    return record


class ImagePromptRendererTests(unittest.TestCase):
    def render(self, specs: list[dict], names: dict[str, str] | None = None) -> str:
        return image_renderer.render(
            specs,
            title="EP001 · 资产图片提示词",
            source="image-prompt-specs.jsonl",
            prompt_language="zh",
            note=None,
            names=names,
        )

    def test_intent_renders_as_prose_not_a_mapping(self) -> None:
        # Printing the mapping leaks Python syntax into a creator document.
        text = self.render([asset_spec()])
        self.assertIn("- **用途**：跨集保持身份；分镜阶段", text)
        self.assertNotIn("{'reuse_job'", text)

    def test_the_heading_prefers_the_asset_display_name(self) -> None:
        text = self.render([asset_spec()], names={"CHAR-A": "乔凡尼"})
        self.assertIn("## `乔凡尼` · `character_sheet`", text)
        self.assertIn("- **绑定**：`CHAR-A` + `LOOK-A`", text)

    def test_a_spec_with_no_variant_records_prints_no_variant_block(self) -> None:
        # An empty 变体/编辑说明 block reads as a variant with nothing recorded.
        self.assertNotIn("变体/编辑说明", self.render([asset_spec()]))

    def test_a_variant_delta_must_name_an_observable_change(self) -> None:
        spec = asset_spec(variant_deltas=[{"field": "wardrobe_layers"}])
        with self.assertRaises(image_renderer.RenderError):
            self.render([spec])

    def test_a_reference_binding_without_its_control_split_is_refused(self) -> None:
        # An unannotated reference is the one that quietly imports composition
        # or wardrobe from a plate bound only for identity.
        spec = asset_spec(reference_bindings=[{"slot_id": "REF-1", "order": 1}])
        with self.assertRaises(image_renderer.RenderError):
            self.render([spec])

    def test_an_annotated_reference_states_what_it_may_not_control(self) -> None:
        spec = asset_spec(
            reference_bindings=[
                {
                    "slot_id": "REF-1",
                    "order": 1,
                    "role": "identity",
                    "may_control": "角色设计",
                    "must_not_control": "构图",
                    "inspection": "unverified",
                }
            ]
        )
        text = self.render([spec])
        self.assertIn("不得导入 `构图`", text)
        self.assertIn("检查状态 `unverified`", text)

    def test_asset_and_lookdev_specs_cannot_share_one_document(self) -> None:
        # Their metadata answers different questions.
        with self.assertRaises(image_renderer.RenderError):
            self.render([asset_spec(), asset_spec(spec_id="L-1", lookdev_axis="x")])

    def test_a_duplicate_spec_id_is_refused(self) -> None:
        with self.assertRaises(image_renderer.RenderError):
            self.render([asset_spec(), asset_spec()])


class KeyframeShotLookupTests(unittest.TestCase):
    def test_a_keyframe_whose_shot_is_missing_is_refused(self) -> None:
        # Falling back to an empty shot costs the prompt its place and its
        # visibility lines while the document still looks finished.
        with self.assertRaises(keyframe_renderer.RenderError):
            keyframe_renderer.render(
                [keyframe("SHOT-1")], {}, episode_id="EP001",
                prompt_language="zh", note=None,
            )
