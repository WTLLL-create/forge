"""Contract tests for the review endpoints."""
from __future__ import annotations

import time
import unittest

from fastapi.testclient import TestClient

from backend import forge_service
from backend.main import app

PROJECT = "forge_v7_3_d2026"
TIMEOUT_SECONDS = 60


class ReviewApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        runs = forge_service.list_runs(PROJECT)
        cls.run_id = runs[0]["run_id"] if runs else None

    def test_unknown_run(self) -> None:
        response = self.client.post("/api/runs/not-a-real-run/review", params={"project": PROJECT})
        self.assertEqual(response.status_code, 404)

    def test_unknown_project(self) -> None:
        response = self.client.post(
            f"/api/runs/{self.run_id or 'x'}/review", params={"project": "../../etc"}
        )
        self.assertEqual(response.status_code, 404)

    def test_invalid_run_id(self) -> None:
        response = self.client.post("/api/runs/bad%20id/review", params={"project": PROJECT})
        self.assertEqual(response.status_code, 404)

    def test_trigger_then_read(self) -> None:
        if not self.run_id:
            self.skipTest("no runs available")
        response = self.client.post(f"/api/runs/{self.run_id}/review", params={"project": PROJECT})
        # A second trigger while the worker is busy must not start a parallel run.
        self.assertIn(response.status_code, (202, 409))

        deadline = time.time() + TIMEOUT_SECONDS
        body = None
        while time.time() < deadline:
            got = self.client.get(f"/api/runs/{self.run_id}/review", params={"project": PROJECT})
            self.assertEqual(got.status_code, 200)
            body = got.json()
            if body["status"]["status"] in ("completed", "failed"):
                break
            time.sleep(1)

        self.assertIsNotNone(body)
        self.assertEqual(body["status"]["status"], "completed", msg=body.get("status"))
        review = body["review"]
        plan = body["plan"]
        self.assertIsNotNone(review)
        self.assertIsNotNone(plan)
        self.assertIn("issues", review)
        self.assertIn("tool_trace", review)
        self.assertGreater(len(review["tool_trace"]), 0)
        self.assertFalse(plan["applied"], "the plan must never claim to be applied")
        self.assertEqual(plan["schema"], "forge-revision-plan/v1")

    def test_trace(self) -> None:
        if not self.run_id:
            self.skipTest("no runs available")
        response = self.client.get(
            f"/api/runs/{self.run_id}/review/trace", params={"project": PROJECT}
        )
        if response.status_code == 404:
            self.skipTest("no review has been run yet")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertGreater(body["steps"], 0)
        self.assertIn("tool", body["trace"][0])


if __name__ == "__main__":
    unittest.main()
