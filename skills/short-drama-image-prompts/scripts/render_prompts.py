#!/usr/bin/env python3
"""Render the derived asset image prompt Markdown from accepted specs.

`image-prompts.md` is declared derived text: the stage contract calls the
rendered prompts a cache. Rendering it by hand writes the same prompt sentence
twice — once into `generic_prompt`, once into the Markdown — and lets the two
copies drift, so the prompt a creator approved and the prompt that ships need
not be the same one.

This script only projects fields the accepted specs already carry. It never
invents, reorders, or rewrites creative content, and it refuses a spec that is
missing a field the template requires instead of emitting a blank line.

The section heading uses the bound identity `record_id`. The template calls it
a display name, but a name lives in the assets bible rather than in the spec,
and resolving one here would mean this stage inventing a fact it does not own.

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
    """A spec cannot be projected without inventing content."""


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


def body_hash(document: str) -> str:
    """Hash the projected body, excluding the self-referential header block."""

    marker = document.find("\n## ")
    body = document[marker:] if marker != -1 else document
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def recipe_label(records: list[dict[str, Any]]) -> str:
    labels = set()
    for record in records:
        recipe = record.get("recipe")
        if not isinstance(recipe, dict) or not recipe.get("version"):
            raise RenderError(f"spec {record.get('spec_id')} has no recipe.version")
        labels.add(f"{recipe.get('name')}@{recipe['version']}")
    if len(labels) != 1:
        raise RenderError(
            f"image-prompt-specs.jsonl must declare one recipe, found {sorted(labels)}"
        )
    return labels.pop()


def _reference_line(bindings: Any, *, where: str) -> str:
    if not bindings:
        return ABSENT
    parts: list[str] = []
    for binding in bindings:
        if not isinstance(binding, dict):
            raise RenderError(f"{where} has a malformed reference binding")
        observation = binding.get("reference_observation_ref")
        status = (
            text(observation)
            if observation
            else f"{text(binding.get('admission_status'))} + "
            f"{text(binding.get('unresolved_risks'))}"
        )
        parts.append(
            f"`{text(binding.get('slot_id'))} / {text(binding.get('order'))} / "
            f"{text((binding.get('artifact_ref') or {}).get('record_id'))}` 只决定 "
            f"`{text(binding.get('role'))} / {text(binding.get('may_control'))}`；"
            f"不得导入 `{text(binding.get('must_not_control'))}`；检查状态 `{status}`"
        )
    return "；".join(parts)


def _notes(record: dict[str, Any]) -> str:
    notes = [
        f"{text(item.get('rule_id'))}={text(item.get('choice'))}（{text(item.get('rationale'))}）"
        for item in record.get("creator_overrides") or []
        if isinstance(item, dict)
    ]
    return " · ".join(notes) if notes else ABSENT


def render_specs(
    specs: list[dict[str, Any]], *, episode: str, source_hash: str
) -> str:
    label = recipe_label(specs)
    lines = [
        f"# {episode} · 资产图片提示词",
        "",
        f"> 来源：`image-prompt-specs.jsonl` 已接受快照 `{source_hash}`",
        f"> 配方：`{label}` · 当前文本 `{{body_hash}}`",
        "> 范围：仅提示词，不生成图片或调用媒体服务",
        "",
    ]
    for spec in specs:
        spec_id = require(spec, "spec_id", where="an image spec")
        where = f"spec {spec_id}"
        purpose = require(spec, "purpose", where=where)
        binding = require(spec, "asset_binding", where=where)
        if not isinstance(binding, dict):
            raise RenderError(f"{where} has a malformed asset_binding")
        identity = binding.get("identity_ref") or {}
        variant = binding.get("variant_ref") or {}
        identity_id = identity.get("record_id") if isinstance(identity, dict) else None
        if not identity_id:
            raise RenderError(f"{where} has no asset_binding.identity_ref.record_id")
        variant_id = variant.get("record_id") if isinstance(variant, dict) else None
        handling = require(spec, "text_handling", where=where)
        if not isinstance(handling, dict):
            raise RenderError(f"{where} has a malformed text_handling")
        treatment = handling.get("render_treatment") or {}
        intent = spec.get("intent") or {}

        lines.extend(
            [
                f"## `{identity_id}` · `{purpose}`",
                "",
                f"- **规格**：`{spec_id}`",
                f"- **绑定**：`{identity_id}`"
                + (f" + `{variant_id}`" if variant_id else ""),
                f"- **用途**：{text(intent.get('reuse_job') if isinstance(intent, dict) else None)}",
                f"- **参考图用途**：{_reference_line(spec.get('reference_bindings'), where=where)}",
                f"- **文字来源政策**：`{text(handling.get('source_mode'))}`",
                f"- **本次呈现**：`{text(treatment.get('mode') if isinstance(treatment, dict) else None)}`"
                f"（{text(handling.get('source_policy_ref', {}).get('record_id'))} → "
                f"{text(treatment.get('mode') if isinstance(treatment, dict) else None)}）",
                f"- **注意**：{_notes(spec)}",
                "",
                "### 可复制通用提示词",
                "",
                f"> {text(require(spec, 'generic_prompt', where=where))}",
                "",
            ]
        )
        edit = spec.get("edit")
        if isinstance(edit, dict) and any(
            edit.get(key) for key in ("changes", "preserve", "continuity_impact", "target_ref")
        ):
            target = edit.get("target_ref") or {}
            lines.extend(
                [
                    "### 变体/编辑说明",
                    "",
                    f"- **相对基准**：{text(target.get('record_id') if isinstance(target, dict) else None)}",
                    f"- **变化**：{text(edit.get('changes'))}",
                    f"- **必须保持**：{text(edit.get('preserve'))}",
                    f"- **连续性影响**：{text(edit.get('continuity_impact'))}",
                    "",
                ]
            )
        lines.extend(["---", ""])
    document = "\n".join(lines)
    return document.replace("{body_hash}", body_hash(document))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render derived asset image prompt Markdown from accepted specs."
    )
    parser.add_argument("records", type=Path, help="image-prompt-specs.jsonl")
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
        document = render_specs(
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
                        "reason": "rendered text does not match the accepted specs",
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
