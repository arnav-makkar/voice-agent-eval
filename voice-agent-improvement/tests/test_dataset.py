import collections
import unittest

from dataset.generate_scenarios import build_scenario


class DatasetContractTests(unittest.TestCase):
    def setUp(self):
        self.scenarios = [build_scenario(index) for index in range(150)]

    def test_declared_dimensions_are_balanced(self):
        self.assertEqual(
            collections.Counter(item["split"] for item in self.scenarios),
            {"development": 90, "regression": 30, "held_out": 30},
        )
        self.assertEqual(
            set(collections.Counter(
                item["public_environment"]["runtime_inputs"]["dpdBucket"]
                for item in self.scenarios
            ).values()),
            {50},
        )
        self.assertEqual(
            set(collections.Counter(item["private_user_state"]["intent"] for item in self.scenarios).values()),
            {15},
        )
        self.assertEqual(
            set(collections.Counter(
                item["private_user_state"]["persona"]["communication_style"]
                for item in self.scenarios
            ).values()),
            {30},
        )
        self.assertEqual(
            set(collections.Counter(
                item["private_user_state"]["persona"]["persona_id"]
                for item in self.scenarios
            ).values()),
            {5},
        )

    def test_all_cases_are_tv_only_and_ledger_arithmetic_is_exact(self):
        for scenario in self.scenarios:
            inputs = scenario["public_environment"]["runtime_inputs"]
            self.assertEqual(inputs["productName"], "Samsung 55-inch 4K Smart TV")
            self.assertEqual(
                int(inputs["outstandingAmount"]),
                int(inputs["emiAmount"]) + int(inputs["lateChargeAmount"]),
            )
            self.assertTrue(scenario["task"]["connected_call_assumption"])

    def test_hidden_state_and_claim_boundaries_are_explicit(self):
        for scenario in self.scenarios:
            private = scenario["private_user_state"]
            provenance = private["persona"]["provenance"]
            self.assertEqual(private["visibility"], "caller_simulator_only")
            self.assertEqual(provenance["source"], "synthetic_local")
            self.assertIn("not a MatrAIx record", provenance["claim_boundary"])
            self.assertIn("not tau2 benchmark compatible", scenario["provenance"]["framework_design"])

    def test_runtime_entities_are_fictional(self):
        forbidden_real_names = {"KreditBee", "Flipkart"}
        for scenario in self.scenarios:
            serialized = str(scenario)
            for name in forbidden_real_names:
                self.assertNotIn(name, serialized)


if __name__ == "__main__":
    unittest.main()
