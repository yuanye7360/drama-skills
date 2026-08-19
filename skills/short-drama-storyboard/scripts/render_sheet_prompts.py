#!/usr/bin/env python3
"""Render `storyboard-sheet-prompts.md` from accepted storyboard sheet records.

The sheet prompt is long, highly structured, and read by an image model that is
sensitive to layout. Leaving the assembly to free composition is what made two
successive renders of the same records disagree about the things the format
contract already fixes: whether the copyable body sits in a fence or a
blockquote, whether an inapplicable field is omitted or filled with a
placeholder, whether the colour legend is stated once globally or restated in
every panel. None of that needs a reading of the drama, so this script does it
exactly and the reference document keeps only the parts that need judgment.

Language is deliberately not handled here. The records carry prose in the
creator language; a prompt body in a different language is a translation, not
an assembly, so the script refuses that case with an explanation instead of
emitting confident text in the wrong language.

The script reads creator files and writes only where told.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


# Creators run these scripts on whatever interpreter their machine provides, so
# an unsupported version must say so instead of failing inside an import.
MINIMUM_PYTHON = (3, 10)
if sys.version_info < MINIMUM_PYTHON:
    raise SystemExit(
        "short-drama needs Python {}.{} or newer; this interpreter is {}.{}".format(
            *MINIMUM_PYTHON, sys.version_info.major, sys.version_info.minor
        )
    )

SCHEMA_VERSION = "1.0.0"
DEFAULT_PROMPT_LANGUAGE = "en"

# A field whose value is one of these carries no instruction: it is the record
# saying "not applicable" in prose. Rendering it puts the word 无 in front of an
# image model as if it were something to draw, so the field is dropped instead.
PLACEHOLDERS = frozenset(
    {"无", "固定", "固定机位", "不适用", "none", "n/a", "fixed", "static"}
)

# Colour keys are a closed set: the legend they belong to is stated once in the
# global block, so a panel names only the arrows it actually carries.
ANNOTATION_ORDER = ("body_motion", "camera", "composition", "light", "vfx_energy")
ANNOTATION_LABEL = {
    "body_motion": "红",
    "camera": "蓝",
    "composition": "绿",
    "light": "橙",
    "vfx_energy": "黄",
}

# Exclusions are stored as machine keys so a mixed-language literal cannot be
# copied verbatim into a prompt. Rendering turns them into short sentences.
EXCLUSION_SENTENCE = {
    "panel_body_text": "格内除颜色标注外无正文文字、标签、图标、注释。",
    "timestamps": "无时间戳。",
    "dialogue": "无对白文字。",
    "singing": "无演唱。",
    "extra_characters": "无镜头资产绑定之外的额外人物。",
    "enemies": "无敌人。",
    "logos_watermarks": "无标志。无水印。",
    "final_look_shading": "无最终画风上色。",
    "finished_illustration_density": "无成品级插画，无密集细节。",
    "panel_background_fill": "无分镜格底色。",
    "duplicate_or_ghost_subject": "无重复或重影形象。",
    "before_after_comparison": "无“前后对比”复制图。",
}

PANEL_PROSE_FIELDS = (
    "action_composition",
    "dynamic_elements",
    "environment",
    "vfx_elements",
)


class RenderError(ValueError):
    """The inputs cannot be rendered at all, as opposed to rendering oddly."""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise RenderError(f"unreadable JSON: {path}") from error


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise RenderError(f"unreadable JSONL: {path}") from error
    records: list[dict[str, Any]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise RenderError(f"{path}:{number}: unreadable JSONL record") from error
        if not isinstance(record, dict):
            raise RenderError(f"{path}:{number}: record is not an object")
        records.append(record)
    if not records:
        raise RenderError(f"no sheet records in {path}")
    return records


def _meaningful(value: Any) -> bool:
    """Whether a field carries an instruction rather than a stand-in for none."""

    if not isinstance(value, str):
        return bool(value)
    text = value.strip()
    if not text:
        return False
    if text.casefold() in PLACEHOLDERS:
        return False
    # "无（此格纯反应定格）" is the same non-instruction wearing a parenthesis.
    return not text.startswith(("无（", "无("))


def _require(record: dict[str, Any], key: str, where: str) -> Any:
    if key not in record:
        raise RenderError(f"{where}: missing required field {key!r}")
    return record[key]


def _sentence(value: str) -> str:
    return value.strip().rstrip("。")


def _panel_lines(panel: dict[str, Any], number: int, where: str) -> list[str]:
    head = "PANEL %02d — %s" % (number, _require(panel, "shot_size", where))
    movement = panel.get("camera_movement")
    if _meaningful(movement):
        head += " / " + str(movement).strip()
    lines = [head]

    prose = [
        _sentence(str(panel[field]))
        for field in PANEL_PROSE_FIELDS
        if _meaningful(panel.get(field))
    ]
    if not prose:
        raise RenderError(f"{where}: panel {number} has no action/composition prose")
    lines.append("。".join(prose) + "。")

    annotations = panel.get("annotations") or {}
    carried = [
        "%s-%s" % (ANNOTATION_LABEL[key], str(annotations[key]).strip())
        for key in ANNOTATION_ORDER
        if _meaningful(annotations.get(key))
    ]
    if carried:
        lines.append("标注：" + "；".join(carried))
    return lines


def render_sheet(sheet: dict[str, Any], aspect_ratio: str) -> list[str]:
    sid = _require(sheet, "sheet_id", "<sheet>")
    where = f"sheet {sid}"
    group = _require(sheet, "narrative_group", where)
    grid = _require(sheet, "grid", where)
    opening = _require(sheet, "opening", where)
    header = _require(sheet, "header", where)
    panels = _require(sheet, "panels", where)
    if not panels:
        raise RenderError(f"{where}: no panels")

    shot_ids = [p["shot_ref"]["record_id"] for p in panels]
    out = [
        "## `%s` · %s组：%s（%d 格）"
        % (sid, group.get("group_id", "?"), group.get("title", ""), len(panels)),
        "",
        "- **格↔镜头**：`"
        + " · ".join("P%d→%s" % (i, x) for i, x in enumerate(shot_ids, start=1))
        + "`",
    ]
    plan = sheet.get("scene_visual_plan_ref")
    out.append(
        "- **视觉计划**：%s"
        % ("无（本场未触发 scene-visual-plan 层）" if not plan else json.dumps(plan, ensure_ascii=False))
    )
    out += ["", "### 可复制通用提示词", "", "```text"]

    references = _require(sheet, "reference_declarations", where)
    out.append(
        "创建以%s为重点的粗略叙事故事板。使用提供的参考图像作为角色与场景依据：%s；"
        "下文一律用名字引用，不再重复 @tag。"
        % (
            _sentence(str(_require(opening, "focus", where))),
            "、".join(
                "%s=%s" % (r["name"], r["reference_tag"]) for r in references
            ),
        )
    )
    out.append("")

    titles = _require(header, "title_lines", where)
    if len(titles) != 2:
        raise RenderError(f"{where}: header needs exactly two quoted title lines")
    empty = "、".join(grid.get("empty_cells") or []) or "无"
    out.append(
        "%s 竖屏故事板纸张，%d列×%d行 网格共 %d 个电影风格面板，左→右、上→下依次填满，"
        "空格位 %s 留空。每格严格同一取景比例 %s、尺寸统一，无混合比例。格标题固定写 "
        "`SHOT-<id> / 景别 / 动作节点名`。页眉排版适配画风，含细分割线与清晰层级，"
        "图形元素置于分镜格之外，只放这两行引号标题：“%s” “%s”，不添加其他页眉文本。"
        % (
            aspect_ratio,
            _require(grid, "cols", where),
            _require(grid, "rows", where),
            _require(grid, "filled", where),
            empty,
            aspect_ratio,
            titles[0],
            titles[1],
        )
    )
    out.append("")

    style = str(_require(sheet, "previs_style", where))
    out.append(
        "画面本体仅为黑白规划稿：%s。保持轻量、动态、未完成，像早期调度预览。"
        "特效一律用石墨排线团块表现，不用最终画风的材质光词。"
        % _sentence(style.split("：", 1)[-1])
    )
    out.append("")

    # The identity lock is read before the panels, not filed behind the
    # exclusions: a panel cannot be read until the reader knows who is who.
    anchors = sheet.get("character_anchors") or []
    if anchors:
        out.append(
            "角色靠固定灰度加剪影逐格认人，全张一致：%s。"
            % "；".join(
                "%s＝%s，剪影为%s"
                % (a["name"], a["tonal_value"], "、".join(a["silhouette_features"]))
                for a in anchors
            )
        )
        out.append("")

    out.append(
        "直接从%s开始，不要以空镜头、平静状态或缓慢介绍开场。%s。"
        "每格都要有可见的定格动作张力与强烈动量，避免完全静止站姿。"
        % (
            _sentence(str(opening["focus"])),
            _sentence(str(_require(opening, "through_line", where))),
        )
    )
    out += ["", "面板进展：", ""]
    for number, panel in enumerate(panels, start=1):
        out += _panel_lines(panel, number, where)
        out.append("")

    progression = _require(sheet, "element_progression", where)
    out.append(
        "元素进展：早期格 %s；中期格 %s；晚期格 %s。"
        % (
            _sentence(str(progression["early"])),
            _sentence(str(progression["mid"])),
            _sentence(str(progression["late"])),
        )
    )
    out.append("摄影词表：%s。" % "、".join(_require(sheet, "cinematography", where)))
    light = sheet.get("global_light")
    environment = "、".join(_require(sheet, "environment_keywords", where))
    tail = "全组光向统一为%s。" % _sentence(str(light)) if _meaningful(light) else ""
    out.append(
        "环境保持最小化、氛围化：%s，不要让画面过于拥挤。%s" % (environment, tail)
    )
    out.append(
        "标注颜色系统：红=身体/主体运动方向。蓝=相机运动方向。绿=构图/组成笔记。"
        "橙=光线方向。黄=VFX/能量效果。黑=简短镜头笔记与面板标签。"
    )
    exclusions = _require(sheet, "exclusions", where)
    unknown = [key for key in exclusions if key not in EXCLUSION_SENTENCE]
    if unknown:
        raise RenderError(
            f"{where}: unknown exclusion keys {unknown}; exclusions are machine keys, "
            "not prompt literals"
        )
    out.append("".join(EXCLUSION_SENTENCE[key] for key in exclusions))
    out += ["```", "", "---", ""]
    return out


def render(
    sheets: list[dict[str, Any]],
    *,
    episode_id: str,
    aspect_ratio: str,
    prompt_language: str,
    note: str | None,
) -> str:
    out = [
        "# %s · 场次故事板 previs" % episode_id,
        "",
        "> 来源：`storyboard-sheets.jsonl`",
        "> 配方：`storyboard-sheet-generic@%s`" % SCHEMA_VERSION,
        "> 范围：粗略规划草图；不生成图片，不上最终画风，不写时间动作",
        "> 语言：可复制正文跟随 `#/format/prompt_language: %s`" % prompt_language,
        "",
    ]
    if note:
        out += ["> %s" % note, ""]
    for sheet in sheets:
        out += render_sheet(sheet, aspect_ratio)
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render storyboard sheet prompts from accepted sheet records."
    )
    parser.add_argument("sheets", type=Path, help="storyboard-sheets.jsonl")
    parser.add_argument(
        "--project", type=Path, required=True, help="short-drama.json"
    )
    parser.add_argument("--episode-id", default=None)
    parser.add_argument("--out", type=Path, default=None, help="default: stdout")
    parser.add_argument("--note", default=None, help="one creator-facing note line")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        sheets = _load_jsonl(args.sheets)
        project = _load_json(args.project)
        if not isinstance(project, dict):
            raise RenderError("project file is not an object")
        language = project.get("language")
        fmt = project.get("format") or {}
        prompt_language = fmt.get("prompt_language") or DEFAULT_PROMPT_LANGUAGE
        aspect_ratio = fmt.get("aspect_ratio") or "9:16"

        # Assembly can reuse the record's prose only while the prompt language and
        # the language those records were written in are the same. Emitting them
        # under a different prompt_language would ship confident text in the wrong
        # language, which is the failure this contract exists to prevent.
        if language != prompt_language:
            raise RenderError(
                "sheet records carry %r prose but prompt_language is %r; supply "
                "records already written in %r, or set the two equal. Rendering "
                "cannot translate." % (language, prompt_language, prompt_language)
            )

        episode_id = args.episode_id
        if episode_id is None:
            first = sheets[0].get("sheet_id", "")
            parts = [p for p in first.split("-") if p.startswith("EP")]
            episode_id = parts[0] if parts else "EP"

        text = render(
            sheets,
            episode_id=episode_id,
            aspect_ratio=aspect_ratio,
            prompt_language=prompt_language,
            note=args.note,
        )
    except RenderError as error:
        print(str(error), file=sys.stderr)
        return 2

    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.write_text(text, encoding="utf-8")
        print(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "sheets": len(sheets),
                    "panels": sum(len(s.get("panels") or []) for s in sheets),
                    "out": str(args.out),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
