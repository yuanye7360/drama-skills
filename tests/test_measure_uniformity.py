"""The uniformity measure has to separate content from reference plumbing.

A record family looks uniform for two very different reasons: because every
record genuinely carries the same amount of drama, or because most of each
record is version plumbing that repeats by design. Only the first is worth
asking about, so the measure must not be fooled by the second.
"""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SUITE = Path(__file__).resolve().parents[1]
TOOL = SUITE / "tools/measure_uniformity.py"
SPEC = importlib.util.spec_from_file_location("short_drama_measure_uniformity", TOOL)
assert SPEC and SPEC.loader
measure_uniformity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(measure_uniformity)


def write(path: Path, records: list[dict[str, object]]) -> Path:
    path.write_text(
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records) + "\n",
        encoding="utf-8",
    )
    return path


class MeasureUniformityTests(unittest.TestCase):
    def measure(self, records: list[dict[str, object]]) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            path = write(Path(directory) / "records.jsonl", records)
            return measure_uniformity.measure(path)

    def test_plumbing_does_not_count_as_content(self) -> None:
        """A long hash must not make a one-word record look substantial."""

        plumbing = {
            "owner": "short-drama-storyboard",
            "artifact": "剧集/EP001/storyboard/shots.jsonl",
            "hash": "b" * 64,
        }

        self.assertEqual(measure_uniformity.content_size(plumbing), 0)
        self.assertEqual(measure_uniformity.content_size({"purpose": "她停手", **plumbing}), 3)

    def test_a_form_filled_evenly_reports_a_low_cv(self) -> None:
        records = [
            {"shot_id": f"SHOT-{index}", "purpose": "观众看见她犹豫了一下"}
            for index in range(5)
        ]

        result = self.measure(records)

        self.assertLess(result["content_chars"]["cv"], 0.05)
        self.assertEqual(result["content_chars"]["max_over_min"], 1.0)

    def test_uneven_prose_reports_a_high_cv(self) -> None:
        records = [
            {"shot_id": "SHOT-1", "purpose": "过场"},
            {"shot_id": "SHOT-2", "purpose": "她终于把合同推回桌面" * 20},
            {"shot_id": "SHOT-3", "purpose": "他没有接"},
        ]

        result = self.measure(records)

        self.assertGreater(result["content_chars"]["cv"], 0.5)

    def test_fields_identical_in_every_record_are_reported_as_ceremony(self) -> None:
        records = [
            {"shot_id": f"SHOT-{index}", "purpose": f"目的{index}", "delivery_surface": "9:16"}
            for index in range(4)
        ]

        result = self.measure(records)

        self.assertIn("delivery_surface", result["ceremony"]["identical_in_every_record"])
        self.assertNotIn("purpose", result["ceremony"]["identical_in_every_record"])

    def test_fields_empty_in_every_record_are_reported_separately(self) -> None:
        records = [
            {"shot_id": f"SHOT-{index}", "purpose": f"目的{index}", "exclusions": []}
            for index in range(4)
        ]

        result = self.measure(records)

        self.assertIn("exclusions", result["ceremony"]["always_empty"])

    def test_a_markdown_shot_table_reads_as_records(self) -> None:
        """A shot table is the same fixed form wearing different punctuation."""

        table = (
            "# EP001\n\n说明段落，不是表格。\n\n"
            "| 鏡號 | 秒數 | 動作 |\n"
            "|---|---|---|\n"
            "| SC001-01 | 4s | 他趴在桌上 |\n"
            "| SC001-02 | 3s | 老师点名 |\n"
            "| SC001-03 | 2s | 他站起来，答不出 |\n"
        )

        records = measure_uniformity.load_markdown_table(table)

        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["鏡號"], "SC001-01")
        self.assertEqual(records[2]["動作"], "他站起来，答不出")

    def test_field_variety_catches_near_boilerplate_exact_equality_misses(self) -> None:
        """A column can say the same thing in most rows without being constant."""

        records = [
            {"shot": "1", "light": "基準光態", "purpose": "建立疲憊"},
            {"shot": "2", "light": "基準光態", "purpose": "點名的壓力"},
            {"shot": "3", "light": "基準光態", "purpose": "沉默的選擇"},
            {"shot": "4", "light": "基準光態,略收窄", "purpose": "情緒頂點"},
        ]

        result = self.measure(records)

        # Not identical in every record, so exact equality does not flag it...
        self.assertNotIn("light", result["ceremony"]["identical_in_every_record"])
        # ...but two distinct values over four rows is the signal that matters.
        self.assertEqual(result["field_variety"]["light"], 0.5)
        self.assertIn("light", result["low_variety_fields"])
        self.assertNotIn("purpose", result["low_variety_fields"])

    def test_too_few_records_says_so_instead_of_reporting_a_number(self) -> None:
        result = self.measure([{"shot_id": "SHOT-1", "purpose": "唯一一条"}])

        self.assertIn("too few records", result["note"])
        self.assertNotIn("content_chars", result)


if __name__ == "__main__":
    unittest.main()
