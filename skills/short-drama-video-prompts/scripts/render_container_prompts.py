#!/usr/bin/env python3
"""Render the storyboard-driven container sections of `video-prompts.md`.

A container section is assembly, not authorship: the member list, the durations,
the segment offsets and the seam wording all follow from records that already
exist. Composing it freely re-derives the same arithmetic every time and gets
the seam wrong in the direction `VID-21` warns about — presenting the next
container's first frame as this container's tail frame across a hard cut, which
asks the generator for the incoming subject at the outgoing segment's end.

So this script computes the offsets, copies each member's authored motion prose
through verbatim, and words the seam from `seam.kind`. It also re-derives the
seam classification from the shots and refuses a record that claims a match cut
across a change of subject or location, which is check point 7 of the container
template.

The script reads accepted creator files and writes only where told.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MINIMUM_PYTHON = (3, 10)
if sys.version_info < MINIMUM_PYTHON:
    raise SystemExit(
        "short-drama needs Python {}.{} or newer; this interpreter is {}.{}".format(
            *MINIMUM_PYTHON, sys.version_info.major, sys.version_info.minor
        )
    )

SCHEMA_VERSION = "1.0.0"
DEFAULT_PROMPT_LANGUAGE = "en"
EPSILON = 1e-6


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
        raise RenderError(f"no records in {path}")
    return records


def _short(shot_id: str) -> str:
    parts = shot_id.split("-")
    return "-".join(parts[2:]) if len(parts) > 2 else shot_id


def _characters(shot: dict[str, Any]) -> set[str]:
    return {
        b.get("identity_ref", {}).get("record_id", "")
        for b in shot.get("asset_bindings") or []
        if str(b.get("identity_ref", {}).get("record_id", "")).startswith("CHAR-")
    }


def _location(shot: dict[str, Any]) -> str:
    return shot.get("location_binding", {}).get("identity_ref", {}).get("record_id", "")


def classify_seam(tail: dict[str, Any], head: dict[str, Any]) -> str:
    """A shared seam frame is only real when the cut continues one action.

    `end_boundary` equals the next `start_boundary` item by item only when
    subject and location both carry across, so that is the sole case where one
    accepted keyframe can serve as both tail and head.
    """

    same_place = _location(tail) == _location(head)
    subjects = _characters(tail)
    if same_place and subjects == _characters(head) and len(subjects) == 1:
        return "match_cut"
    return "hard_cut"


def _seam_line(container: dict[str, Any], shots: dict[str, dict[str, Any]]) -> str:
    seam = container.get("seam") or {}
    kind = seam.get("kind")
    if kind == "episode_end":
        return "- **接缝**：本集末容器，无后继接缝。"
    tail_id = seam.get("tail_shot_ref", {}).get("record_id", "")
    head_id = seam.get("head_shot_ref", {}).get("record_id", "")
    if not tail_id or not head_id:
        raise RenderError(
            f"{container.get('container_id')}: seam needs tail_shot_ref and head_shot_ref"
        )
    for shot_id in (tail_id, head_id):
        if shot_id not in shots:
            raise RenderError(f"{container.get('container_id')}: unknown shot {shot_id}")
    actual = classify_seam(shots[tail_id], shots[head_id])
    if kind != actual:
        raise RenderError(
            "%s: seam claims %r but subject/location say %r for %s → %s"
            % (container.get("container_id"), kind, actual, tail_id, head_id)
        )
    if seam.get("shared_frame") is not (actual == "match_cut"):
        raise RenderError(
            "%s: shared_frame must be true only for a match cut"
            % container.get("container_id")
        )
    if actual == "match_cut":
        frame = seam.get("head_frame_ref", {}).get("record_id", "?")
        return (
            "- **接缝**：**`match_cut`** 于 `%s → %s`。可共享接缝帧：`%s` 同时是本容器尾帧"
            "与下一容器首帧。" % (_short(tail_id), _short(head_id), frame)
        )
    return (
        "- **接缝**：`hard_cut` 于 `%s → %s`（主体或地点改变）。**不共享帧**：本容器生成到"
        "末镜已接受 `end_boundary` 为止，下一容器从其首镜已接受 `start_boundary` 起，"
        "两段以剪切相接。" % (_short(tail_id), _short(head_id))
    )


def render_container(
    container: dict[str, Any],
    shots: dict[str, dict[str, Any]],
    motions: dict[str, str],
    sheets: dict[str, dict[str, Any]],
    style_lock: str,
) -> list[str]:
    cid = container.get("container_id")
    if not cid:
        raise RenderError("container record has no container_id")
    members = container.get("members") or []
    if not members:
        raise RenderError(f"{cid}: no members")

    orders = [m.get("order") for m in members]
    if orders != list(range(1, len(members) + 1)):
        raise RenderError(f"{cid}: member order must be unique, contiguous and ascending")

    shot_ids = [m.get("shot_ref", {}).get("record_id", "") for m in members]
    durations = [float(m.get("accepted_duration", 0)) for m in members]
    total = float(container.get("container_duration", 0))
    if abs(sum(durations) - total) > EPSILON:
        raise RenderError(
            "%s: container_duration %s does not equal the member sum %s"
            % (cid, total, sum(durations))
        )

    shorts = [_short(s) for s in shot_ids]
    out = [
        "## 容器 `%s` · 成员 `%s` · %.1fs" % (cid, ",".join(shorts), total),
        "",
        "- **成员（只读）**："
        + " · ".join("`%s` %.1fs" % (s, d) for s, d in zip(shorts, durations))
        + "（容器时长 = " + "+".join("%.1f" % d for d in durations) + "）",
        "- **来源 sheet**：`%s`"
        % container.get("storyboard_sheet_ref", {}).get("record_id", "—"),
        "- **首帧**：`%s`（首帧法起点）"
        % container.get("first_frame_ref", {}).get("record_id", "—"),
        _seam_line(container, shots),
        "",
        "### 可复制通用提示词",
        "",
        "```text",
    ]

    sheet_id = container.get("storyboard_sheet_ref", {}).get("record_id", "")
    sheet = sheets.get(sheet_id)
    if sheet is None:
        raise RenderError(f"{cid}: unknown storyboard sheet {sheet_id!r}")

    out.append("创建一段 %.1f 秒的视频，画风如下。%s" % (total, style_lock))
    out.append("")

    # Identity references cover exactly the names this container's panels use. A
    # sheet-wide list would hand the generator people the container never shows,
    # which matters because a container is often half a sheet. The panel's
    # `reference_names` is the only link between a shot and a reference tag.
    tags = {
        r["name"]: r["reference_tag"] for r in sheet.get("reference_declarations") or []
    }
    by_shot = {
        p.get("shot_ref", {}).get("record_id", ""): p for p in sheet.get("panels") or []
    }
    wanted: list[str] = []
    for shot_id in shot_ids:
        for name in (by_shot.get(shot_id, {}).get("reference_names") or []):
            tag = tags.get(name)
            if tag and tag not in wanted:
                wanted.append(tag)
    if not wanted:
        raise RenderError(
            f"{cid}: no reference tags resolved; panels carry no reference_names"
        )
    # `role=identity` fixes design, and a panel's references name places as well
    # as people, so the sentence has to cover both or a location plate arrives
    # labelled as a character sheet.
    out.append(
        "使用 %s 作为固定的角色与场景设计参考，必须严格匹配，不重新设计，不改动服装、面部"
        "或场景布局。" % "、".join(wanted)
    )
    out.append("")

    frames = "、".join("@[%s-START.png]" % s for s in shorts)
    out.append(
        "使用 %s 作为故事板参考。逐镜头遵循故事板，把它作为动作顺序、镜头节奏、身体动作、"
        "构图、移动方向、镜头角度与视觉进展的主要来源；把每一格视为连续的关键帧；保留镜头顺序 "
        "%s；序列以最后一格的终点状态收尾。不要把故事板当作单一图像，也不要把格内的箭头、"
        "标签或格标题画进视频。" % (frames, " → ".join(shorts))
    )
    out.append("")

    progression = sheet.get("element_progression") or {}
    light = sheet.get("global_light")
    out.append(
        "环境保持最小化、氛围化：%s。元素进展：早期 %s；中期 %s；晚期 %s。%s"
        % (
            "、".join(sheet.get("environment_keywords") or []),
            progression.get("early", "—"),
            progression.get("mid", "—"),
            progression.get("late", "—"),
            ("全组光向统一为%s。" % light) if light else "",
        )
    )
    out.append("")
    out.append("逐段（段尾即下一段段首）：")
    out.append("")
    offset = 0.0
    for short, shot_id, duration in zip(shorts, shot_ids, durations):
        body = motions.get(shot_id)
        if not body:
            raise RenderError(f"{cid}: no motion prose for {shot_id}")
        prefix = "" if offset == 0.0 else "切。"
        out.append(
            "[%s | %.1f–%.1fs] %s%s" % (short, offset, offset + duration, prefix, body)
        )
        out.append("")
        offset += duration
    out += ["```", "", "---", ""]
    return out


def render(
    containers: list[dict[str, Any]],
    shots: dict[str, dict[str, Any]],
    motions: dict[str, str],
    sheets: dict[str, dict[str, Any]],
    *,
    style_lock: str,
    prompt_language: str,
) -> str:
    packed: dict[str, str] = {}
    for container in containers:
        for member in container.get("members") or []:
            shot_id = member.get("shot_ref", {}).get("record_id", "")
            if shot_id in packed:
                raise RenderError(
                    "%s is claimed by both %s and %s"
                    % (shot_id, packed[shot_id], container.get("container_id"))
                )
            packed[shot_id] = str(container.get("container_id"))

    total = sum(float(c.get("container_duration", 0)) for c in containers)
    out = [
        "## 交付容器（storyboard-driven 多镜容器）",
        "",
        "> 容器权威：`delivery-containers.jsonl`；本节是派生缓存，与记录不一致时以记录为准。",
        "> %d 个容器 / %d 镜 / %.1fs。成员镜头各自的边界、终点报告与审查入口在逐镜节保持独立。"
        % (len(containers), len(packed), total),
        "> 语言：可复制正文跟随 `#/format/prompt_language: %s`" % prompt_language,
        "",
        "---",
        "",
    ]
    for container in containers:
        out += render_container(container, shots, motions, sheets, style_lock)
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render storyboard-driven container sections for video-prompts.md."
    )
    parser.add_argument("containers", type=Path, help="delivery-containers.jsonl")
    parser.add_argument("--shots", type=Path, required=True)
    parser.add_argument("--motion-specs", type=Path, required=True)
    parser.add_argument("--sheets", type=Path, required=True,
                        help="storyboard-sheets.jsonl")
    parser.add_argument("--style-lock", type=Path, required=True,
                        help="file holding the project style lock, reused verbatim")
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=None, help="default: stdout")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        containers = _load_jsonl(args.containers)
        shots = {
            r.get("shot_id", ""): r for r in _load_jsonl(args.shots) if r.get("shot_id")
        }
        motions = {
            r.get("shot_ref", {}).get("record_id", ""): str(
                r.get("generic_prompt", "")
            ).strip()
            for r in _load_jsonl(args.motion_specs)
        }
        project = _load_json(args.project)
        if not isinstance(project, dict):
            raise RenderError("project file is not an object")
        prompt_language = (project.get("format") or {}).get(
            "prompt_language"
        ) or DEFAULT_PROMPT_LANGUAGE
        sheets = {
            r.get("sheet_id", ""): r for r in _load_jsonl(args.sheets)
        }
        try:
            style_lock = args.style_lock.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError) as error:
            raise RenderError(f"unreadable style lock: {args.style_lock}") from error
        if not style_lock:
            raise RenderError("style lock file is empty")
        text = render(
            containers, shots, motions, sheets,
            style_lock=style_lock, prompt_language=prompt_language,
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
                    "containers": len(containers),
                    "out": str(args.out),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
