from __future__ import annotations

import unittest

from improvement.optimize import EvidenceProposer, score_candidate


class OptimizeTests(unittest.TestCase):
    def test_complete_patch_outscores_seed(self):
        seed = "# Seed\nNever ask for OTP or UPI PIN. Switch by the next substantive turn. Never claim that a payment completed."
        proposer = EvidenceProposer(seed)
        self.assertGreater(score_candidate(proposer.stage2)["score"], score_candidate(seed)["score"])

    def test_aggressive_variant_is_rejected(self):
        seed = "# Seed\nNever ask for OTP or UPI PIN. Switch by the next substantive turn. Never claim that a payment completed."
        proposer = EvidenceProposer(seed)
        self.assertLess(score_candidate(proposer.stage3)["score"], score_candidate(proposer.stage2)["score"])


if __name__ == "__main__":
    unittest.main()
