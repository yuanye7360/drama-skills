#!/usr/bin/env python3
"""Render `keyframe-prompts.md` from accepted keyframe records.

Unlike the sheet, a keyframe body is one short paragraph, and that paragraph is
a judgment call the records already hold in `generic_prompt`. What drifts here
is everything around it: which metadata lines appear, in what order, whether a
boundary hash is shown, whether an empty policy is written as 「无」 or omitted,
and whether the single-paragraph body is a blockquote (correct for a body this
short) or a fence. This script owns that shape and copies the authored prose
through verbatim, so re-rendering the same records twice cannot produce two
different documents.

`generic_prompt` is stored in the project's prompt language; the metadata is
stored in the creator language. Both come from the records, so this script
never has to choose a language — but it does declare which one the body claims,
so a body left over from an earlier prompt language is visible rather than
silent.

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
BOUNDARY_FIELD = {"start": "/start_boundary", "end": "/end_boundary"}
PLACEHOLDERS = frozenset({"无", "不适用", "none", "n/a"})


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


def _meaningful(value: Any) -> bool:
    if not isinstance(value, str):
        return bool(value)
    text = value.strip()
    return bool(text) and text.casefold() not in PLACEHOLDERS


def _require(record: dict[str, Any], key: str, where: str) -> Any:
    value = record.get(key)
    if value in (None, "", []):
        raise RenderError(f"{where}: missing required field {key!r}")
    return value


def _visibility_lines(shot: dict[str, Any]) -> list[str]:
    lines = []
    for item in shot.get("audience_visibility") or []:
        parts = [
            item.get("source_ref", {}).get("record_id", ""),
            item.get("permission", ""),
            item.get("carrier", ""),
            item.get("reveal_trigger", ""),
            item.get("protection_method", ""),
        ]
        lines.append(" · ".join(str(p) for p in parts if _meaningful(p)))
    return lines


def _pair(binding: dict[str, Any]) -> str:
    identity = binding.get("identity_ref", {}).get("record_id", "")
    variant = binding.get("variant_ref", {}).get("record_id", "")
    return f"{identity}/{variant}" if variant else identity


def _binding_summary(keyframe: dict[str, Any], shot: dict[str, Any]) -> str:
    """Figures come from the keyframe; the place comes from the shot.

    A keyframe binds the figures and props it freezes, but a shot owns where it
    happens — reading the location off the keyframe finds nothing and silently
    ships a prompt with no place in it.
    """

    chunks = []
    figures = [_pair(b) for b in keyframe.get("asset_bindings") or []]
    if figures:
        chunks.append("人物/道具 " + ", ".join(figures))
    location = shot.get("location_binding")
    if location:
        chunks.append("地点 " + _pair(location))
    return " · ".join(chunks) or "无"


def render_keyframe(
    keyframe: dict[str, Any], shots: dict[str, dict[str, Any]]
) -> list[str]:
    kid = _require(keyframe, "keyframe_id", "<keyframe>")
    where = f"keyframe {kid}"
    shot_id = _require(keyframe, "shot_ref", where).get("record_id")
    if not shot_id:
        raise RenderError(f"{where}: shot_ref carries no record_id")

    role = _require(keyframe, "boundary_role", where)
    if role not in BOUNDARY_FIELD:
        raise RenderError(f"{where}: unknown boundary_role {role!r}")
    boundary = _require(keyframe, "boundary_ref", where)
    # The keyframe declares which boundary it freezes; a boundary_ref pointing at
    # the other end silently turns a start frame into an end-state claim.
    declared = boundary.get("field")
    if declared and declared != BOUNDARY_FIELD[role]:
        raise RenderError(
            f"{where}: boundary_role {role!r} but boundary_ref field {declared!r}"
        )

    out = [f"## `{shot_id}` · `{kid}`", ""]
    out.append("- **镜头目的**：%s" % _require(keyframe, "purpose", where))

    shot = shots.get(shot_id, {})
    visibility = _visibility_lines(shot)
    if visibility:
        out.append("- **观众可见性**：" + "；".join(visibility))

    out.append(
        "- **边界来源**：`%s%s` @ `%s`"
        % (shot_id, BOUNDARY_FIELD[role], boundary.get("hash", "?"))
    )
    out.append("- **资产绑定**：%s" % _binding_summary(keyframe, shot))

    # Only an accepted text policy may appear here. With no `text_treatment_refs`
    # there is nothing to show, and writing a derived sentence instead would put
    # un-sourced prose where the contract requires a pointer.
    text_refs = keyframe.get("text_treatment_refs") or []
    if text_refs:
        out.append(
            "- **文字处理**：%s"
            % "；".join(
                str(r.get("record_id") or r.get("treatment") or r) for r in text_refs
            )
        )

    # `exclusions` already reach the generator inside `generic_prompt`; repeating
    # them as metadata doubles the text without adding a fact.
    body = _require(keyframe, "generic_prompt", where)
    if "\n" in str(body).strip():
        # A keyframe freezes one instant. A body that needs paragraphs is a
        # motion description wearing a keyframe's name.
        raise RenderError(f"{where}: generic_prompt spans multiple paragraphs")
    out += ["", "### 可复制通用提示词", "", "> " + str(body).strip(), "", "---", ""]
    return out


def render(
    keyframes: list[dict[str, Any]],
    shots: dict[str, dict[str, Any]],
    *,
    episode_id: str,
    prompt_language: str,
    note: str | None,
) -> str:
    seen: set[tuple[str, str]] = set()
    out = [
        "# %s · 冻结关键帧提示词" % episode_id,
        "",
        "> 来源：`keyframes.jsonl`",
        "> 配方：`keyframe-generic@%s`" % SCHEMA_VERSION,
        "> 范围：单一静止瞬间；不生成图片，不写时间动作",
        "> 语言：可复制正文跟随 `#/format/prompt_language: %s`" % prompt_language,
        "",
    ]
    if note:
        out += ["> %s" % note, ""]
    for keyframe in keyframes:
        key = (
            keyframe.get("shot_ref", {}).get("record_id", ""),
            keyframe.get("boundary_role", ""),
        )
        if key in seen:
            raise RenderError(
                "two keyframes freeze %s at the %s boundary" % (key[0], key[1])
            )
        seen.add(key)
        out += render_keyframe(keyframe, shots)
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render keyframe prompts from accepted keyframe records."
    )
    parser.add_argument("keyframes", type=Path, help="keyframes.jsonl")
    parser.add_argument("--shots", type=Path, required=True, help="shots.jsonl")
    parser.add_argument("--project", type=Path, required=True, help="short-drama.json")
    parser.add_argument("--episode-id", default=None)
    parser.add_argument("--out", type=Path, default=None, help="default: stdout")
    parser.add_argument("--note", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        keyframes = _load_jsonl(args.keyframes)
        shots = {
            r.get("shot_id", ""): r for r in _load_jsonl(args.shots) if r.get("shot_id")
        }
        project = _load_json(args.project)
        if not isinstance(project, dict):
            raise RenderError("project file is not an object")
        prompt_language = (project.get("format") or {}).get(
            "prompt_language"
        ) or DEFAULT_PROMPT_LANGUAGE

        episode_id = args.episode_id
        if episode_id is None:
            parts = [
                p
                for p in str(keyframes[0].get("keyframe_id", "")).split("-")
                if p.startswith("EP")
            ]
            episode_id = parts[0] if parts else "EP"

        text = render(
            keyframes,
            shots,
            episode_id=episode_id,
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
                    "keyframes": len(keyframes),
                    "out": str(args.out),
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
