from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from framework.tool_service import create_app


class ToolServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.client = TestClient(create_app(db_path=Path(self.temp.name) / "tools.db", secret="test-secret"))
        self.headers = {"X-Agent-Tool-Key": "test-secret"}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def seed(self, run_id: str = "RUN-001", account_id: str = "EC-001") -> None:
        response = self.client.post(
            "/v1/evaluation/runs",
            headers=self.headers,
            json={
                "run_id": run_id,
                "account_id": account_id,
                "outstanding_amount": "3066",
                "payment_status": "unpaid",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_tool_effect_and_audit_are_isolated(self) -> None:
        self.seed()
        response = self.client.post(
            "/v1/tools/record-promise-to-pay",
            headers=self.headers,
            json={"run_id": "RUN-001", "account_id": "EC-001", "date": "22-08-2026", "event_id": "evt-1"},
        )
        self.assertEqual(response.status_code, 200)
        state = self.client.get("/v1/evaluation/runs/RUN-001", headers=self.headers).json()
        self.assertEqual(state["initial_state"]["promise_to_pay_date"], None)
        self.assertEqual(state["state"]["promise_to_pay_date"], "22-08-2026")
        self.assertEqual(state["events"][0]["tool_name"], "record_promise_to_pay")

    def test_idempotent_event_does_not_duplicate_side_effect(self) -> None:
        self.seed()
        payload = {"run_id": "RUN-001", "account_id": "EC-001", "date": "22-08-2026", "event_id": "evt-1"}
        first = self.client.post("/v1/tools/record-promise-to-pay", headers=self.headers, json=payload)
        second = self.client.post("/v1/tools/record-promise-to-pay", headers=self.headers, json=payload)
        self.assertEqual(first.json(), second.json())
        state = self.client.get("/v1/evaluation/runs/RUN-001", headers=self.headers).json()
        self.assertEqual(len(state["events"]), 1)

    def test_cross_run_account_mismatch_is_rejected(self) -> None:
        self.seed()
        response = self.client.post(
            "/v1/tools/check-payment-status",
            headers=self.headers,
            json={"run_id": "RUN-001", "account_id": "EC-WRONG"},
        )
        self.assertEqual(response.status_code, 409)

    def test_terminal_disposition_is_persisted(self) -> None:
        self.seed()
        response = self.client.post(
            "/v1/tools/record-call-outcome",
            headers=self.headers,
            json={"run_id": "RUN-001", "account_id": "EC-001", "disposition": "payment_ready"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"recorded": True, "disposition": "payment_ready"})
        state = self.client.get("/v1/evaluation/runs/RUN-001", headers=self.headers).json()
        self.assertEqual(state["state"]["disposition"], "payment_ready")
        self.assertEqual(state["events"][0]["tool_name"], "record_call_outcome")

    def test_authentication_is_required(self) -> None:
        response = self.client.get("/v1/evaluation/runs/RUN-001")
        self.assertEqual(response.status_code, 401)

    def test_synthetic_tool_bypass_keeps_run_admin_authenticated(self) -> None:
        client = TestClient(
            create_app(
                db_path=Path(self.temp.name) / "synthetic-tools.db",
                secret="test-secret",
                allow_unauthenticated_tools=True,
            )
        )
        seed = client.post(
            "/v1/evaluation/runs",
            headers=self.headers,
            json={
                "run_id": "RUN-SYNTH",
                "account_id": "EC-SYNTH",
                "outstanding_amount": "3066",
                "payment_status": "unpaid",
            },
        )
        self.assertEqual(seed.status_code, 200)
        tool = client.post(
            "/v1/tools/check-payment-status",
            json={"run_id": "RUN-SYNTH", "account_id": "EC-SYNTH"},
        )
        self.assertEqual(tool.status_code, 200)
        self.assertEqual(tool.json()["payment_status"], "unpaid")
        state = client.get("/v1/evaluation/runs/RUN-SYNTH")
        self.assertEqual(state.status_code, 401)


if __name__ == "__main__":
    unittest.main()
