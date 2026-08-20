from __future__ import annotations

import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from sarvam_voice_agents.cli import _append_manifest, _validate_run_id


class RunIdTests(unittest.TestCase):
    def test_accepts_local_run_id(self) -> None:
        self.assertEqual(_validate_run_id("BL-CTRL-01"), "BL-CTRL-01")

    def test_allows_none_for_dry_run(self) -> None:
        self.assertIsNone(_validate_run_id(None))

    def test_rejects_whitespace_and_unsafe_characters(self) -> None:
        with self.assertRaises(ValueError):
            _validate_run_id("BL CTRL 01")

    def test_appends_local_manifest_record(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "calls.jsonl"
            _append_manifest(str(path), {"run_id": "BL-CTRL-01"})
            _append_manifest(str(path), {"run_id": "BL-CTRL-02"})
            records = [json.loads(line) for line in path.read_text().splitlines()]
            self.assertEqual(
                [record["run_id"] for record in records],
                ["BL-CTRL-01", "BL-CTRL-02"],
            )


if __name__ == "__main__":
    unittest.main()
