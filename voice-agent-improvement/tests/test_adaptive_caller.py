import asyncio
import unittest

from framework.evaluation.adaptive_caller import CallerAction, ScriptedAdaptivePolicy


class AdaptiveCallerTests(unittest.TestCase):
    def test_scripted_policy_is_stateful_and_stops(self):
        policy = ScriptedAdaptivePolicy([CallerAction("speak", "haan"), CallerAction("barge_in", "ek minute")])
        first = asyncio.run(policy.next_action())
        second = asyncio.run(policy.next_action())
        terminal = asyncio.run(policy.next_action())
        self.assertEqual(first.action, "speak")
        self.assertEqual(second.action, "barge_in")
        self.assertEqual(terminal.action, "end")

    def test_spoken_actions_require_text(self):
        with self.assertRaises(ValueError):
            CallerAction("speak")

    def test_invalid_delay_is_rejected(self):
        with self.assertRaises(ValueError):
            CallerAction("wait", delay_ms=10001)


if __name__ == "__main__":
    unittest.main()
