"""API contract tests for the Forge console."""
from __future__ import annotations

import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend import forge_service

PROJECT = "forge_v7_3_d2026"


class ConsoleApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)
        runs = forge_service.list_runs(PROJECT)
        cls.run_id = runs[0]["run_id"] if runs else None

    def test_health(self) -> None:
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_projects_include_forge(self) -> None:
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 200)
        names = [item["name"] for item in response.json()]
        self.assertIn(PROJECT, names)

    def test_runs_list_shape(self) -> None:
        response = self.client.get("/api/runs", params={"project": PROJECT})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIsInstance(body, list)
        if body:
            self.assertIn("run_id", body[0])
            self.assertIn("stages_pass", body[0])

    def test_run_detail(self) -> None:
        if not self.run_id:
            self.skipTest("no runs available")
        response = self.client.get(f"/api/runs/{self.run_id}", params={"project": PROJECT})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["run_id"], self.run_id)
        self.assertIn("stages", body)
        self.assertIn("gates", body)
        self.assertIn("artifacts", body)
        main_gates = [g for g in body["gates"] if g["kind"] == "gate"]
        self.assertGreaterEqual(len(main_gates), 8)

    def test_artifact_download(self) -> None:
        if not self.run_id:
            self.skipTest("no runs available")
        manifest = self.client.get(
            f"/api/runs/{self.run_id}", params={"project": PROJECT}
        ).json()
        files = []

        def walk(nodes):
            for node in nodes:
                if node["type"] == "dir":
                    walk(node.get("children") or [])
                else:
                    files.append(node["path"])

        walk(manifest["artifacts"])
        if not files:
            self.skipTest("run has no artifacts")
        response = self.client.get(
            f"/api/runs/{self.run_id}/download",
            params={"project": PROJECT, "path": files[0]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 0)

    def test_path_escape_rejected(self) -> None:
        if not self.run_id:
            self.skipTest("no runs available")
        response = self.client.get(
            f"/api/runs/{self.run_id}/download",
            params={"project": PROJECT, "path": "../../workflow.json"},
        )
        self.assertEqual(response.status_code, 404)

    def test_unknown_run(self) -> None:
        response = self.client.get("/api/runs/not-a-real-run", params={"project": PROJECT})
        self.assertEqual(response.status_code, 404)

    def test_unknown_project(self) -> None:
        response = self.client.get("/api/runs", params={"project": "../../etc"})
        self.assertEqual(response.status_code, 404)

    def test_log_stream(self) -> None:
        if not self.run_id:
            self.skipTest("no runs available")
        detail = self.client.get(
            f"/api/runs/{self.run_id}", params={"project": PROJECT}
        ).json()
        stage = next((s for s in detail["stages"] if s["logs"].get("stdout")), None)
        if not stage:
            self.skipTest("no stage logs available")
        response = self.client.get(
            f"/api/runs/{self.run_id}/logs/{stage['stage']}/stdout",
            params={"project": PROJECT},
        )
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
