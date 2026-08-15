#!/usr/bin/env python3
"""Render the derived storyboard prompt Markdown from accepted records.

`keyframe-prompts.md` and `storyboard-sheet-prompts.md` are declared caches:
the stage contract says the rendered prompts are a projection and the Markdown
is never a second source of truth. Rendering them by hand contradicts that in
two ways that both cost the project:

* the same prompt sentence is written twice — once into `generic_prompt`, once
  into the Markdown — so the drama pays for a transcription pass; and
* the two copies can disagree. The creator reads and approves the Markdown
  while the record of truth is the JSONL, so an approved prompt and a delivered
  prompt can silently differ.

This script removes both. It only projects fields that already exist in the
accepted records; it never invents, reorders, or edits creative content, and it
refuses a record that is missing a field the template requires rather than
papering over it with an empty line.

`--check` re-renders and compares against a file on disk, which turns "the
Markdown is a cache" from a rule a reviewer has to police into one a command
decides.
"""

from __future__ import annotations

import argparse
import hashlib
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

ABSENT = "无"


class RenderError(ValueError):
    """A record cannot be projected without inventing content."""


def load_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise RenderError(f"{path.name} line {number} is not valid JSON") from error
        if not isinstance(record, dict):
            raise RenderError(f"{path.name} line {number} is not a JSON object")
        records.append(record)
    if not records:
        raise RenderError(f"{path.name} has no records to render")
    return records


def require(record: dict[str, Any], key: str, *, where: str) -> Any:
    value = record.get(key)
    if value is None or value == "" or value == []:
        raise RenderError(f"{where} is missing {key}")
    return value


def text(value: Any) -> str:
    """Flatten a scalar or list field into one readable cell."""

    if isinstance(value, list):
        return " / ".join(text(item) for item in value) if value else ABSENT
    if isinstance(value, dict):
        return " / ".join(f"{key}={text(item)}" for key, item in sorted(value.items()))
    if value is None or value == "":
        return ABSENT
    return str(value)


def recipe_version(records: list[dict[str, Any]], *, where: str) -> str:
    versions = {
        str(record.get("derivation", {}).get("recipe_version"))
        for record in records
        if isinstance(record.get("derivation"), dict)
    }
    versions.discard("None")
    if len(versions) != 1:
        raise RenderError(
            f"{where} must declare exactly one derivation.recipe_version, found {sorted(versions)}"
        )
    return versions.pop()


def body_hash(document: str) -> str:
    """Hash the projected body, excluding the self-referential header block.

    The header carries the source hash and this value, so it cannot contain its
    own digest. Everything a hand edit would touch lives below the first
    section heading, so the body is what has to be pinned.
    """

    marker = document.find("\n## ")
    body = document[marker:] if marker != -1 else document
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _asset_binding(binding: Any, *, where: str) -> str:
    if not isinstance(binding, dict):
        raise RenderError(f"{where} has a malformed asset binding")
    identity = binding.get("identity_ref") or {}
    variant = binding.get("variant_ref") or {}
    identity_id = identity.get("record_id") if isinstance(identity, dict) else None
    if not identity_id:
        raise RenderError(f"{where} has an asset binding without an identity record_id")
    variant_id = variant.get("record_id") if isinstance(variant, dict) else None
    return f"{identity_id}+{variant_id}" if variant_id else str(identity_id)


def _visibility_line(entry: Any) -> str:
    if not isinstance(entry, dict):
        return ABSENT
    return " · ".join(
        text(entry.get(key))
        for key in ("fact", "permission", "carrier", "reveal_trigger", "protection_method")
    )


def render_keyframes(
    keyframes: list[dict[str, Any]],
    shots: list[dict[str, Any]],
    *,
    episode: str,
    source_hash: str,
) -> str:
    by_shot = {
        str(shot.get("shot_id")): shot for shot in shots if shot.get("shot_id")
    }
    version = recipe_version(keyframes, where="keyframes.jsonl")
    lines = [
        f"# {episode} · 冻结关键帧提示词",
        "",
        f"> 来源：`keyframes.jsonl` 已接受快照 `{source_hash}`",
        f"> 配方：`keyframe-generic@{version}` · 当前文本 `{{body_hash}}`",
        "> 范围：单一静止瞬间；不生成图片，不写时间动作",
        "",
    ]
    for keyframe in keyframes:
        keyframe_id = require(keyframe, "keyframe_id", where="a keyframe record")
        where = f"keyframe {keyframe_id}"
        shot_ref = require(keyframe, "shot_ref", where=where)
        if not isinstance(shot_ref, dict) or not shot_ref.get("record_id"):
            raise RenderError(f"{where} has no shot_ref.record_id")
        shot_id = str(shot_ref["record_id"])
        role = require(keyframe, "boundary_role", where=where)
        boundary_ref = require(keyframe, "boundary_ref", where=where)
        if not isinstance(boundary_ref, dict) or not boundary_ref.get("hash"):
            raise RenderError(f"{where} has no boundary_ref.hash")
        shot = by_shot.get(shot_id)
        if shot is None:
            raise RenderError(f"{where} references an unknown shot: {shot_id}")
        visibility = shot.get("audience_visibility") or []
        bindings = require(keyframe, "asset_bindings", where=where)
        treatments = keyframe.get("text_treatment_refs") or []

        lines.extend(
            [
                f"## `{shot_id}` · `{keyframe_id}`",
                "",
                f"- **镜头目的**：{text(require(keyframe, 'purpose', where=where))}",
                "- **观众可见性**："
                + (
                    " ｜ ".join(_visibility_line(entry) for entry in visibility)
                    if visibility
                    else ABSENT
                ),
                f"- **边界来源**：`{shot_id}/{role}_boundary` @ `{boundary_ref['hash']}`",
                "- **资产绑定**："
                + " · ".join(_asset_binding(item, where=where) for item in bindings),
                "- **文字处理**："
                + (
                    " · ".join(
                        f"{item.get('record_id', ABSENT)}{item.get('field', '')}"
                        for item in treatments
                        if isinstance(item, dict)
                    )
                    if treatments
                    else ABSENT
                ),
                "",
                "### 可复制通用提示词",
                "",
                f"> {text(require(keyframe, 'generic_prompt', where=where))}",
                "",
                "---",
                "",
            ]
        )
    document = "\n".join(lines)
    return document.replace("{body_hash}", body_hash(document))


def _panel_block(panel: Any, *, where: str) -> list[str]:
    if not isinstance(panel, dict):
        raise RenderError(f"{where} has a malformed panel")
    panel_id = panel.get("panel_id") or ABSENT
    annotations = panel.get("annotations") or {}
    if not isinstance(annotations, dict):
        raise RenderError(f"{where} panel {panel_id} has malformed annotations")
    annotation = "；".join(
        f"{label}-{text(annotations.get(key))}"
        for key, label in (
            ("body_motion", "红色箭头"),
            ("camera", "蓝色箭头"),
            ("composition", "绿色标记"),
            ("light", "橙色标记"),
            ("vfx_energy", "黄色标记"),
        )
        if annotations.get(key)
    )
    return [
        f"> {panel_id}",
        f"> 参考：{text(panel.get('reference_names'))}",
        f"> 景别：{text(panel.get('shot_size'))}",
        f"> 镜头运动：{text(panel.get('camera_movement'))}",
        f"> 动作/构图：{text(panel.get('action_composition'))}",
        f"> 动态元素：{text(panel.get('dynamic_elements'))}",
        f"> 环境：{text(panel.get('environment'))}",
        f"> 特效/元素：{text(panel.get('vfx_elements'))}",
        f"> 镜头笔记：{text(panel.get('shot_note'))}",
        f"> 标注：{annotation or ABSENT}",
        ">",
    ]


def render_sheets(
    sheets: list[dict[str, Any]], *, episode: str, source_hash: str
) -> str:
    version = recipe_version(sheets, where="storyboard-sheets.jsonl")
    lines: list[str] = []
    for sheet in sheets:
        sheet_id = require(sheet, "sheet_id", where="a storyboard sheet record")
        where = f"sheet {sheet_id}"
        group = require(sheet, "narrative_group", where=where)
        if not isinstance(group, dict):
            raise RenderError(f"{where} has a malformed narrative_group")
        group_id = text(group.get("group_id"))
        panels = require(sheet, "panels", where=where)
        opening = require(sheet, "opening", where=where)
        if not isinstance(opening, dict):
            raise RenderError(f"{where} has a malformed opening")
        grid = require(sheet, "grid", where=where)
        if not isinstance(grid, dict):
            raise RenderError(f"{where} has a malformed grid")
        header = require(sheet, "header", where=where)
        if not isinstance(header, dict):
            raise RenderError(f"{where} has a malformed header")
        plan_ref = sheet.get("scene_visual_plan_ref")
        plan = (
            f"`{plan_ref.get('artifact')}` @ `{plan_ref.get('hash')}`"
            if isinstance(plan_ref, dict)
            else ABSENT
        )
        mapping = " · ".join(
            f"{panel.get('panel_id')}→{(panel.get('shot_ref') or {}).get('record_id')}"
            for panel in panels
            if isinstance(panel, dict)
        )
        progression = sheet.get("element_progression") or {}
        if not lines:
            lines.extend(
                [
                    f"# {episode} · 场次故事板 previs · {group_id}组",
                    "",
                    f"> 来源：`storyboard-sheets.jsonl` 已接受快照 `{source_hash}`",
                    f"> 配方：`storyboard-sheet-generic@{version}` · 当前文本 `{{body_hash}}`",
                    "> 范围：粗略规划草图；不生成图片，不上最终画风，不写时间动作",
                    "",
                ]
            )
        lines.extend(
            [
                f"## `{sheet_id}` · {group_id}组：{text(group.get('title'))}"
                f"（{len(panels)} 格）",
                "",
                f"- **格↔镜头**：{mapping}（一格一镜，格顺序=叙事先后）",
                f"- **视觉计划**：{plan}",
                "",
                "### 可复制通用提示词",
                "",
                f"> 创建以{text(opening.get('focus'))}为重点的原始叙事故事板。"
                "使用提供的参考图像作为角色和场景基础。",
                ">",
                f"> {text(grid.get('panel_aspect'))} 故事板纸张，{len(panels)} 个电影风格面板。"
                f"{text(sheet.get('previs_style'))}。",
                ">",
                "> [参考图] 使用以下参考图作为对应角色/场景"
                "（下面各格一律用名字引用，不重复 @tag）：",
            ]
        )
        for declaration in sheet.get("reference_declarations") or []:
            if not isinstance(declaration, dict):
                raise RenderError(f"{where} has a malformed reference declaration")
            lines.append(
                f"> {text(declaration.get('name'))} 参考 {text(declaration.get('reference_tag'))}"
            )
        lines.extend(
            [
                ">",
                "> [页眉] 适配画风的排版、细分割线与清晰层级；图形元素置于分镜格之外。"
                "仅含以下引号文字，不得添加其他页眉文本：",
            ]
        )
        for title in header.get("title_lines") or []:
            lines.append(f'> "{text(title)}"')
        lines.extend(
            [
                ">",
                f"> 直接从{text(opening.get('focus'))}开始。不要以空镜头、平静状态或缓慢介绍开始。",
                ">",
                f"> {text(opening.get('through_line'))}。"
                "每个面板都必须包含可见的静态动作张力和强烈动量，避免完全静止站姿。",
                ">",
                "> 各格内容：",
                ">",
            ]
        )
        for panel in panels:
            lines.extend(_panel_block(panel, where=where))
        lines.extend(
            [
                f"> 元素进展：早期格{text(progression.get('early'))}；"
                f"中期格{text(progression.get('mid'))}；晚期格{text(progression.get('late'))}。",
                f"> 摄影：{text(sheet.get('cinematography'))}。",
                f"> 环境保持最小化、氛围化：{text(sheet.get('environment_keywords'))}；"
                "不要让画面过于拥挤。",
                "> 标注颜色系统：红=身体运动方向；蓝=相机运动方向；绿=构图/组成；"
                "橙=光线方向；黄=VFX/能量；黑=镜头笔记与面板标签。",
                f"> 排除：{text(sheet.get('exclusions'))}。",
                "",
                "---",
                "",
            ]
        )
    document = "\n".join(lines)
    return document.replace("{body_hash}", body_hash(document))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render derived storyboard prompt Markdown from accepted records."
    )
    parser.add_argument("kind", choices=("keyframes", "sheets"))
    parser.add_argument("records", type=Path, help="keyframes.jsonl or storyboard-sheets.jsonl")
    parser.add_argument("--shots", type=Path, help="shots.jsonl; required for keyframes")
    parser.add_argument("--episode", required=True, help="Episode label, e.g. EP001")
    parser.add_argument("--out", type=Path, help="Write the rendered Markdown here")
    parser.add_argument(
        "--check",
        type=Path,
        help=(
            "Compare an existing rendered file against a fresh render and exit 1 on "
            "any difference. This is what makes the Markdown a cache rather than a "
            "second source of truth."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = load_records(args.records)
        source_hash = hashlib.sha256(args.records.read_bytes()).hexdigest()
        if args.kind == "keyframes":
            if args.shots is None:
                raise RenderError("keyframes rendering needs --shots")
            document = render_keyframes(
                records,
                load_records(args.shots),
                episode=args.episode,
                source_hash=source_hash,
            )
        else:
            document = render_sheets(
                records, episode=args.episode, source_hash=source_hash
            )
    except (OSError, RenderError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2

    if args.check is not None:
        try:
            current = args.check.read_text(encoding="utf-8")
        except OSError as error:
            print(f"OSError: {error}", file=sys.stderr)
            return 2
        if current != document:
            print(
                json.dumps(
                    {
                        "status": "stale",
                        "path": str(args.check),
                        "reason": "rendered text does not match the accepted records",
                    },
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )
            return 1
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(document, encoding="utf-8")
    elif args.check is None:
        sys.stdout.write(document)
    print(
        json.dumps(
            {
                "status": "rendered" if args.check is None else "current",
                "records": len(records),
                "rendered_hash": body_hash(document),
                "source_hash": source_hash,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
