from __future__ import annotations

import unittest

from improvement.evaluate import is_direct_ask, is_explicit_commitment


class EvaluatorTests(unittest.TestCase):
    def test_direct_ask_requires_payment_and_now(self):
        self.assertTrue(is_direct_ask("क्या आप अभी app से payment कर सकते हैं?"))
        self.assertTrue(is_direct_ask("Can you pay now through the official app?"))
        self.assertFalse(is_direct_ask("Please review the reminder."))

    def test_commitment_excludes_conditional_check(self):
        ask = "क्या आप अभी app से payment कर सकते हैं?"
        self.assertTrue(is_explicit_commitment("ठीक है अभी app खोलकर pay करता हूँ।", ask))
        self.assertFalse(is_explicit_commitment("ठीक है मैं app में check करता हूँ।", ask))


if __name__ == "__main__":
    unittest.main()
