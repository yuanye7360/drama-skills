#!/usr/bin/env python3
"""Render `image-prompts.md` and `lookdev-prompts.md` from accepted specs.

Both documents wrap an authored prompt body in a metadata block, and the block
is where they drift: whether a spec with no reference bindings prints 「无参考图
绑定」 or omits the line, whether an empty text policy becomes a derived
sentence, whether variant notes appear on a spec that is not a variant. None of
that needs judgment, so the script settles it and copies `generic_prompt`
through verbatim.

Which of the two documents to render is read from the records, not from a flag:
a spec carrying `lookdev_axis` is a Look Development frame and a spec carrying
`asset_binding` is an asset prompt. Mixing the two in one file is refused, since
their metadata answers different questions.

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


def _body(spec: dict[str, Any], where: str, style_lock: str) -> list[str]:
    body = str(_require(spec, "generic_prompt", where)).strip()
    if not body:
        raise RenderError(f"{where}: empty generic_prompt")
    check_style_lock(body, style_lock, where)
    return ["", "### 可复制通用提示词", "", "> " + body, "", "---", ""]


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


def _reference_line(spec: dict[str, Any]) -> str:
    """State what a reference is allowed to decide, or that there is none.

    A reference that arrives without its `may_control` / `must_not_control`
    split is the one that quietly imports composition or wardrobe from a plate
    bound only for identity, so an unannotated binding is refused rather than
    printed.
    """

    bindings = spec.get("reference_bindings") or []
    if not bindings:
        return "- **参考图用途**：无参考图绑定"
    parts = []
    for binding in bindings:
        slot = binding.get("slot_id", "?")
        order = binding.get("order", "?")
        role = binding.get("role")
        may = binding.get("may_control")
        must_not = binding.get("must_not_control")
        if not (role and may and must_not):
            raise RenderError(
                f"reference binding {slot!r} needs role, may_control and must_not_control"
            )
        checked = binding.get("inspection") or "unverified"
        parts.append(
            "`%s / order %s / %s` 只决定 `%s`；不得导入 `%s`；检查状态 `%s`"
            % (slot, order, role, may, must_not, checked)
        )
    return "- **参考图用途**：" + "；".join(parts)


def _intent_text(intent: Any) -> str:
    """`intent` records who reuses this asset and for what, as separate fields.

    Printing the mapping itself leaks Python syntax into a creator document, so
    the known fields are joined and any extra field still appears rather than
    being silently dropped.
    """

    if not isinstance(intent, dict):
        return str(intent)
    order = ["reuse_job", "audience"]
    parts = [str(intent[k]) for k in order if intent.get(k)]
    parts += [f"{k}：{v}" for k, v in intent.items() if k not in order and v]
    return "；".join(parts)


def render_asset_spec(
    spec: dict[str, Any], names: dict[str, str], style_lock: str
) -> list[str]:
    sid = _require(spec, "spec_id", "<spec>")
    where = f"spec {sid}"
    binding = _require(spec, "asset_binding", where)
    identity = binding.get("identity_ref", {}).get("record_id", "")
    variant = binding.get("variant_ref", {}).get("record_id", "")
    # A creator reads the document by name; the ID is kept on the binding line.
    display = spec.get("display_name") or names.get(identity) or identity
    purpose = _require(spec, "purpose", where)

    out = [
        "## `%s` · `%s`" % (display, purpose),
        "",
        "- **规格**：`%s`" % sid,
        "- **绑定**：`%s`%s" % (identity, f" + `{variant}`" if variant else ""),
    ]
    if _meaningful(spec.get("intent")):
        out.append("- **用途**：%s" % _intent_text(spec["intent"]))
    out.append(_reference_line(spec))

    # Only an accepted policy may appear. With no text-bearing surface there is
    # nothing to point at, and a derived sentence would put un-sourced prose
    # where the contract requires a pointer.
    policy = spec.get("text_policy") or {}
    if _meaningful(policy.get("mode")):
        out.append("- **文字来源政策**：`%s`" % policy["mode"])
        if _meaningful(policy.get("treatment")):
            out.append("- **本次呈现**：`%s`" % policy["treatment"])

    notes = [n for n in (spec.get("constraints") or []) if _meaningful(n)]
    if notes:
        out.append("- **注意**：%s" % "；".join(str(n) for n in notes))

    out += _body(spec, where, style_lock)

    # Variant notes belong only to a spec that records one. Each delta names the
    # field it moves, the change an eye can check, and how long it holds; a
    # delta missing the observable change is a claim nobody can verify.
    deltas = [d for d in (spec.get("variant_deltas") or []) if d]
    if deltas:
        block = ["### 变体/编辑说明", ""]
        for delta in deltas:
            field = delta.get("field")
            change = delta.get("observable_change")
            if not (field and change):
                raise RenderError(
                    f"{where}: variant delta needs field and observable_change"
                )
            valid = delta.get("valid_range")
            block.append(
                "- **%s**：%s%s"
                % (field, change, f"（有效区间：{valid}）" if valid else "")
            )
        out = out[:-2] + block + ["", "---", ""]
    return out


def render_lookdev_spec(spec: dict[str, Any], style_lock: str) -> list[str]:
    sid = _require(spec, "spec_id", "<spec>")
    where = f"spec {sid}"
    axis = _require(spec, "lookdev_axis", where)
    out = [
        "## `%s` · %s" % (sid, axis),
        "",
        "- **测试问题**：%s" % _require(spec, "test_question", where),
    ]

    subjects = []
    for binding in spec.get("subject_bindings") or []:
        record_id = binding.get("identity_ref", {}).get("record_id", "")
        role = binding.get("role")
        subjects.append(f"`{record_id}`" + (f"（{role}）" if role else ""))
    contexts = [
        "`%s#%s`" % (c.get("artifact", ""), c.get("record_id", ""))
        for c in spec.get("story_context_refs") or []
    ]
    if subjects or contexts:
        chunks = []
        if subjects:
            chunks.append("、".join(subjects))
        if contexts:
            chunks.append("场景依据 " + "、".join(contexts))
        out.append("- **绑定事实**：%s" % "；".join(chunks))

    for label, key in (("跨轴稳定", "stable_visual_rules"), ("本帧可变", "allowed_variation")):
        values = [v for v in (spec.get(key) or []) if _meaningful(v)]
        if values:
            out.append("- **%s**：%s" % (label, "、".join(str(v) for v in values)))

    out.append(_reference_line(spec).replace("参考图用途", "风格参考权限"))
    if _meaningful(spec.get("unknowns")):
        out.append("- **仍未知**：%s" % spec["unknowns"])
    out += _body(spec, where, style_lock)
    return out


def render(
    specs: list[dict[str, Any]], *, title: str, source: str, prompt_language: str,
    note: str | None, style_lock: str, names: dict[str, str] | None = None,
) -> str:
    kinds = {"lookdev" if s.get("lookdev_axis") else "asset" for s in specs}
    if len(kinds) > 1:
        raise RenderError(
            "asset specs and lookdev specs answer different questions; render them "
            "into separate documents"
        )
    lookdev = kinds == {"lookdev"}

    out = [
        "# %s" % title,
        "",
        "> 来源：`%s`" % source,
        "> 范围：仅提示词，不生成图片或调用媒体服务",
        "> 语言：可复制正文跟随 `#/format/prompt_language: %s`" % prompt_language,
        "",
    ]
    if note:
        out += ["> %s" % note, ""]

    seen: set[str] = set()
    for spec in specs:
        sid = str(spec.get("spec_id", ""))
        if sid in seen:
            raise RenderError(f"duplicate spec_id {sid!r}")
        seen.add(sid)
        out += (
            render_lookdev_spec(spec, style_lock)
            if lookdev
            else render_asset_spec(spec, names or {}, style_lock)
        )
    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render image or Look Development prompt documents from specs."
    )
    parser.add_argument("specs", type=Path, help="image-prompt-specs.jsonl")
    parser.add_argument(
        "--assets", type=Path, nargs="*", default=[],
        help="asset JSONL files supplying display names (设定集/*.jsonl)",
    )
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument(
        "--style-lock", type=Path, default=None,
        help="项目开发/style-lock.jsonl; derived from the project root when omitted",
    )
    parser.add_argument("--title", default=None)
    parser.add_argument("--out", type=Path, default=None, help="default: stdout")
    parser.add_argument("--note", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        document, specs = split_document_record(_load_jsonl(args.specs))
        if not specs:
            raise RenderError(
                f"{args.specs} carries only a document record; there is nothing "
                "to render"
            )
        project = _load_json(args.project)
        if not isinstance(project, dict):
            raise RenderError("project file is not an object")
        prompt_language = (project.get("format") or {}).get(
            "prompt_language"
        ) or DEFAULT_PROMPT_LANGUAGE
        style_lock_path = args.style_lock or derive_project_path(
            args.project, "项目开发", "style-lock.jsonl"
        )
        if style_lock_path is None:
            raise RenderError(
                "no --style-lock given and 项目开发/style-lock.jsonl is not under "
                f"{args.project.resolve().parent}; pass --style-lock explicitly"
            )
        asset_files = list(args.assets) or derive_asset_files(args.project)
        names: dict[str, str] = {}
        for path in asset_files:
            for record in _load_jsonl(path):
                record_id = next(
                    (v for k, v in record.items() if k.endswith("_id")), None
                )
                if record_id and record.get("display_name"):
                    names[str(record_id)] = str(record["display_name"])
        lookdev = bool(specs[0].get("lookdev_axis"))
        # The fallback is spelled at the call site rather than passed in, so the
        # resolved title is a `str` instead of an `Optional[str]` that only
        # happens never to be None.
        title = resolve_header_value(
            flag=args.title, document=document, key="title", fallback=None
        ) or ("项目 Look Development 提示词" if lookdev else "资产图片提示词")
        title_explicit = args.title is not None or bool(document.get("title"))
        text = render(
            specs,
            title=title,
            source=args.specs.name,
            prompt_language=prompt_language,
            note=resolve_header_value(
                flag=args.note, document=document, key="note", fallback=None
            ),
            style_lock=load_style_lock(style_lock_path),
            names=names,
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
                {"schema_version": SCHEMA_VERSION, "specs": len(specs), "out": str(args.out)},
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
