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


DOCUMENT_RECORD_KIND = "document"
_MACHINE_HEADER_MARKERS = ("来源：", "范围：", "语言：", "配方：", "容器权威：")


def split_document_record(
    records: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Peel the optional leading document-metadata record off the content records.

    The document title and the creator-facing note belong to the authoritative
    records, not to whoever last typed the command line. A re-render that has to
    be told them again is a re-render that drops them without saying so.
    """
    document: dict[str, Any] = {}
    content: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        kind = record.get("record_kind")
        if kind is None:
            content.append(record)
            continue
        if kind != DOCUMENT_RECORD_KIND:
            raise RenderError(
                f"record {index}: unknown record_kind {kind!r}; the only metadata "
                f"kind is {DOCUMENT_RECORD_KIND!r}, and guessing would render a "
                "metadata typo as content"
            )
        if index != 0:
            raise RenderError(
                "the document record has to be the first record in the file"
            )
        document = record
    return document, content


def resolve_header_value(
    *, flag: str | None, document: dict[str, Any], key: str, fallback: str | None
) -> str | None:
    """Flag beats the record, the record beats the fallback."""
    if flag is not None:
        return flag
    value = document.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return fallback


def _header_parts(text: str) -> tuple[str | None, list[str]]:
    """The H1 and the creator prose lines of a rendered document's header."""
    title: str | None = None
    prose: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            break
        if title is None and line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("> "):
            body = line[2:].strip()
            if not any(marker in body for marker in _MACHINE_HEADER_MARKERS):
                prose.append(body)
    return title, prose


def guard_header_metadata(
    existing: str, rendered: str, *, title_explicit: bool
) -> None:
    """Refuse to replace a derived document with one that loses its own header.

    Derived text is a cache, but it used to be the only home for the title
    prefix and the creator note, so a bare re-render deleted them and reported
    success. Until every document carries its own metadata record, this guard
    is what stands between a routine re-render and silent loss.
    """
    old_title, old_prose = _header_parts(existing)
    new_title, new_prose = _header_parts(rendered)
    lost = [line for line in old_prose if line not in new_prose]
    if lost:
        raise RenderError(
            "refusing to overwrite: the existing document carries a creator note "
            "these records do not reproduce (%s). Put it in a leading "
            '{"record_kind": "document", "note": "..."} record, or restate it '
            "with --note." % "; ".join(lost)
        )
    if not title_explicit and old_title and new_title != old_title:
        raise RenderError(
            "refusing to overwrite: the existing title %r would become %r, which "
            'is only a fallback. Put it in a leading {"record_kind": "document", '
            '"title": "..."} record, or restate it with --title.'
            % (old_title, new_title)
        )


def derive_project_path(project_file: Path, *relative: str) -> Path | None:
    """A canonical-layout path under the project root, when it is really there.

    Every path this script needs already has one obvious home in a canonical
    project. Making the creator retype them is how a re-render turns into nine
    hand-assembled arguments, and a hand-assembled argument is one that can be
    forgotten. A project on a non-canonical layout gets nothing back and is
    told to pass the flag.
    """
    candidate = project_file.resolve().parent.joinpath(*relative)
    return candidate if candidate.exists() else None


def derive_asset_files(project_file: Path) -> list[Path]:
    """Every bible JSONL, in a stable order so display names resolve the same way."""
    bible = project_file.resolve().parent / "设定集"
    return sorted(bible.glob("*.jsonl")) if bible.is_dir() else []


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


def load_style_lock(path: Path) -> str:
    """Read the one verbatim style lock every prompt body must open with.

    "Reused verbatim across the project" only holds while the text has a place
    to be read from. A loose string retyped per render is the same rule with
    nothing enforcing it.
    """

    records = _load_jsonl(path)
    if len(records) != 1:
        raise RenderError(
            f"{path}: a project has exactly one style lock, found {len(records)}"
        )
    text = str(records[0].get("text") or "").strip()
    if not text:
        raise RenderError(f"{path}: style lock record carries no text")
    return text


def check_style_lock(body: str, style_lock: str, where: str) -> None:
    """Refuse a body that does not open with the lock.

    A body missing it reaches the generator with no look direction at all, and
    the result is stylistically unrelated to the assets rendered beside it —
    visible only once the images come back.
    """

    if not body.strip().startswith(style_lock):
        raise RenderError(
            f"{where}: prompt body must open with the project style lock verbatim"
        )


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
    keyframe: dict[str, Any], shots: dict[str, dict[str, Any]], style_lock: str
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

    # A missing shot silently costs the prompt its place and its visibility
    # lines, and the document still looks finished. Refuse instead.
    if shot_id not in shots:
        raise RenderError(f"{where}: shot {shot_id} is not in the shot list")
    shot = shots[shot_id]
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
    check_style_lock(str(body), style_lock, where)
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
    style_lock: str,
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
        out += render_keyframe(keyframe, shots, style_lock)
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render keyframe prompts from accepted keyframe records."
    )
    parser.add_argument("keyframes", type=Path, help="keyframes.jsonl")
    parser.add_argument(
        "--shots", type=Path, default=None,
        help="shots.jsonl; defaults to the one beside the keyframes",
    )
    parser.add_argument("--project", type=Path, required=True, help="short-drama.json")
    parser.add_argument(
        "--style-lock", type=Path, default=None,
        help="项目开发/style-lock.jsonl; derived from the project root when omitted",
    )
    parser.add_argument("--episode-id", default=None)
    parser.add_argument("--out", type=Path, default=None, help="default: stdout")
    parser.add_argument("--note", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        document, keyframes = split_document_record(_load_jsonl(args.keyframes))
        if not keyframes:
            raise RenderError(
                f"{args.keyframes} carries only a document record; there is "
                "nothing to render"
            )
        paths = {
            "--shots": args.shots
            or args.keyframes.resolve().parent / "shots.jsonl",
            "--style-lock": args.style_lock
            or derive_project_path(args.project, "项目开发", "style-lock.jsonl"),
        }
        for flag, path in paths.items():
            if path is None or not path.exists():
                raise RenderError(
                    f"{flag} was not given and its canonical location is not there; "
                    f"pass {flag} explicitly"
                )
        shots = {
            r.get("shot_id", ""): r
            for r in _load_jsonl(paths["--shots"])
            if r.get("shot_id")
        }
        project = _load_json(args.project)
        if not isinstance(project, dict):
            raise RenderError("project file is not an object")
        prompt_language = (project.get("format") or {}).get(
            "prompt_language"
        ) or DEFAULT_PROMPT_LANGUAGE

        episode_id = resolve_header_value(
            flag=args.episode_id, document=document, key="episode_id", fallback=None
        )
        title_explicit = episode_id is not None
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
            note=resolve_header_value(
                flag=args.note, document=document, key="note", fallback=None
            ),
            style_lock=load_style_lock(paths["--style-lock"]),
        )
        if args.out is not None and args.out.exists():
            guard_header_metadata(
                args.out.read_text(encoding="utf-8"),
                text,
                title_explicit=title_explicit,
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
