import tempfile
import unittest
from pathlib import Path

from framework.evaluation.freeze_evaluator import DEFAULT_VERSION, freeze


class EvaluatorFreezeTests(unittest.TestCase):
    def test_freeze_is_versioned_and_immutable(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "freeze.json"
            record = freeze(path)
            self.assertEqual(
                record["evaluator_version"],
                f"evaluation-metrics.v3/framework-eva-adapter.v1/samvaad-duplex.v{DEFAULT_VERSION}",
            )
            self.assertEqual(len(record["bundle_sha256"]), 64)
            self.assertTrue(record["release_rules"]["validation_before_scoring"])
            with self.assertRaises(FileExistsError):
                freeze(path)


if __name__ == "__main__":
    unittest.main()
