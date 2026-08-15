#!/usr/bin/env python3
"""Render the derived video prompt Markdown from accepted motion records.

`video-prompts.md` is declared a cache: the stage contract calls it derived
text and says it is not the storyboard authority. Rendering it by hand costs
the project twice — the prompt sentence is written once into `generic_prompt`
and again into the Markdown, and the two copies can then disagree, so the
prompt a creator approved and the prompt that ships need not be the same one.

This script only projects fields the accepted records already carry. It never
invents, reorders, or rewrites creative content, and it refuses a record that
is missing a field the template requires instead of emitting a blank line.

`--check` re-renders and compares against a file on disk, so "this file is a
cache" becomes something a command decides rather than something a reviewer
has to notice.
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
    """Hash the projected body, excluding the self-referential header block."""

    marker = document.find("\n## ")
    body = document[marker:] if marker != -1 else document
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _reference_line(bindings: Any, *, where: str) -> str:
    if not bindings:
        return ABSENT
    parts: list[str] = []
    for binding in bindings:
        if not isinstance(binding, dict):
            raise RenderError(f"{where} has a malformed reference binding")
        admission = text(binding.get("admission_status"))
        observation = binding.get("reference_observation_ref")
        status = (
            text(observation)
            if observation
            else f"{admission} + {text(binding.get('unresolved_risks'))}"
        )
        parts.append(
            f"`{text(binding.get('slot_id'))} / {text(binding.get('order'))} / "
            f"{text((binding.get('artifact_ref') or {}).get('record_id'))}` 只决定 "
            f"`{text(binding.get('role'))} / {text(binding.get('may_control'))}`；"
            f"不得导入 `{text(binding.get('must_not_control'))}`；检查状态 `{status}`"
        )
    return "；".join(parts)


def _coverage_line(scope: Any, *, where: str) -> str | None:
    if not scope:
        return None
    if not isinstance(scope, dict):
        raise RenderError(f"{where} has a malformed coverage_scope")
    obligations = " · ".join(
        f"{text((item.get('source_ref') or {}).get('record_id'))} → "
        f"{text(item.get('motion_field'))}/{text(item.get('disposition'))}"
        for item in scope.get("source_obligations") or []
        if isinstance(item, dict)
    )
    supplements = scope.get("supplements_motion_ids") or []
    return (
        f"- **覆盖范围（仅补拍/替代版）**：`{text(scope.get('mode'))}`；"
        f"母版/补充 `{text(scope.get('master_motion_id'))} / {text(supplements)}`；"
        f"逐项内容 `{obligations or ABSENT}`；"
        f"替代请求 `{text(scope.get('replacement_intent'))}`"
    )


def _audio_ids(entries: Any) -> str:
    ids = [
        f"{text(entry.get('kind'))}:{text((entry.get('source_ref') or {}).get('record_id'))}"
        for entry in entries or []
        if isinstance(entry, dict)
    ]
    return " · ".join(ids) if ids else ABSENT


def _notes(record: dict[str, Any]) -> str:
    notes = [
        f"{text(item.get('rule_id'))}={text(item.get('choice'))}（{text(item.get('rationale'))}）"
        for item in record.get("creator_overrides") or []
        if isinstance(item, dict)
    ]
    return " · ".join(notes) if notes else ABSENT


def render_motions(
    motions: list[dict[str, Any]],
    shots: list[dict[str, Any]],
    *,
    episode: str,
    source_hash: str,
) -> str:
    by_shot = {str(shot.get("shot_id")): shot for shot in shots if shot.get("shot_id")}
    version = recipe_version(motions, where="motion-specs.jsonl")
    lines = [
        f"# {episode} · 视频提示词",
        "",
        f"> 来源：`motion-specs.jsonl` 已接受快照 `{source_hash}`",
        f"> 配方：`motion-generic@{version}` · 当前文本 `{{body_hash}}`",
        "> 范围：仅提示词，不生成视频/音频，不调用媒体服务",
        "",
    ]
    for motion in motions:
        motion_id = require(motion, "motion_id", where="a motion record")
        where = f"motion {motion_id}"
        shot_ref = require(motion, "shot_ref", where=where)
        if not isinstance(shot_ref, dict) or not shot_ref.get("record_id"):
            raise RenderError(f"{where} has no shot_ref.record_id")
        shot_id = str(shot_ref["record_id"])
        shot = by_shot.get(shot_id)
        if shot is None:
            raise RenderError(f"{where} references an unknown shot: {shot_id}")
        keyframe_ref = require(motion, "keyframe_ref", where=where)
        if not isinstance(keyframe_ref, dict) or not keyframe_ref.get("hash"):
            raise RenderError(f"{where} has no keyframe_ref.hash")
        boundaries = require(motion, "boundary_refs", where=where)
        if not isinstance(boundaries, dict):
            raise RenderError(f"{where} has malformed boundary_refs")
        duration = (boundaries.get("duration") or {}).get("value_seconds")
        if duration is None:
            raise RenderError(f"{where} has no boundary_refs.duration.value_seconds")
        report = require(motion, "end_report", where=where)
        if not isinstance(report, dict):
            raise RenderError(f"{where} has a malformed end_report")
        projection = report.get("projection") or {}
        next_start = (boundaries.get("next_start") or {}).get("record_id")

        lines.append(f"## `{shot_id}` · {text(shot.get('purpose'))}")
        lines.append("")
        lines.append(f"- **运动规格**：`{motion_id}`")
        coverage = _coverage_line(motion.get("coverage_scope"), where=where)
        if coverage:
            lines.append(coverage)
        lines.extend(
            [
                f"- **起始帧**：`{text(keyframe_ref.get('record_id'))}` @ `{keyframe_ref['hash']}`",
                f"- **参考图用途**：{_reference_line(motion.get('reference_bindings'), where=where)}",
                f"- **时长（只读）**：`{duration}s`",
                f"- **边界核对**：`end {text(report.get('comparison'))}`",
                f"- **声音引用**：{_audio_ids(motion.get('audio'))}",
                f"- **注意**：{_notes(motion)}",
                "",
                "### 可复制通用提示词",
                "",
                f"> {text(require(motion, 'generic_prompt', where=where))}",
                "",
                "### 只读结束报告",
                "",
                f"- **位置/姿态**：{text(projection.get('position'))} / "
                f"{text(projection.get('pose'))} → 来源：{text(report.get('comparison'))}",
                f"- **目光/双手/持物**：{text(projection.get('gaze'))} / "
                f"{text(projection.get('hands'))} / {text(projection.get('held_props'))} "
                f"→ 来源：{text(report.get('comparison'))}",
                f"- **可见状态**：{text(projection.get('visible_state'))} "
                f"→ 来源：{text(report.get('comparison'))}",
                f"- **下一镜**：仅比较 `{text(next_start)}`，未改写",
                "",
                "---",
                "",
            ]
        )
    document = "\n".join(lines)
    return document.replace("{body_hash}", body_hash(document))


def render_containers(
    containers: list[dict[str, Any]], *, episode: str, source_hash: str
) -> str:
    lines = [
        f"# {episode} · 视频提示词 · 交付容器",
        "",
        f"> 来源：`delivery-containers.jsonl` 已接受快照 `{source_hash}`",
        "> 范围：仅提示词，不生成视频/音频，不调用媒体服务",
        "",
    ]
    for container in containers:
        container_id = require(container, "container_id", where="a container record")
        where = f"container {container_id}"
        members = require(container, "members", where=where)
        ordered = sorted(
            (member for member in members if isinstance(member, dict)),
            key=lambda member: member.get("order", 0),
        )
        if len(ordered) != len(members):
            raise RenderError(f"{where} has a malformed member")
        names = ",".join(
            str((member.get("shot_ref") or {}).get("record_id")) for member in ordered
        )
        detail = " · ".join(
            f"`{(member.get('shot_ref') or {}).get('record_id')} "
            f"@{(member.get('shot_ref') or {}).get('hash')} "
            f"{member.get('accepted_duration')}s`"
            for member in ordered
        )
        lines.extend(
            [
                f"## 容器 `{container_id}` · 成员 `{names}` · "
                f"{text(container.get('container_duration'))}s",
                "",
                f"- **成员（只读）**：{detail}（容器时长 = 各成员已接受时长之和）",
                "- **成员运动规格**："
                + " · ".join(
                    f"`{(member.get('motion_ref') or {}).get('record_id')}`"
                    for member in ordered
                ),
                "",
                "---",
                "",
            ]
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render derived video prompt Markdown from accepted records."
    )
    parser.add_argument("kind", choices=("motions", "containers"))
    parser.add_argument("records", type=Path)
    parser.add_argument("--shots", type=Path, help="shots.jsonl; required for motions")
    parser.add_argument("--episode", required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--check",
        type=Path,
        help=(
            "Compare an existing rendered file against a fresh render and exit 1 on "
            "any difference."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        records = load_records(args.records)
        source_hash = hashlib.sha256(args.records.read_bytes()).hexdigest()
        if args.kind == "motions":
            if args.shots is None:
                raise RenderError("motion rendering needs --shots")
            document = render_motions(
                records,
                load_records(args.shots),
                episode=args.episode,
                source_hash=source_hash,
            )
        else:
            document = render_containers(
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
