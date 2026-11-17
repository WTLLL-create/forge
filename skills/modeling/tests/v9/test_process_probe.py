"""A liveness check must never signal or terminate the process it inspects."""
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.runtime.production_workflow import ProductionWorkflow


class ProcessProbeTests(unittest.TestCase):
    def test_live_child_survives_probe(self):
        child = subprocess.Popen([sys.executable, '-c',
                                  'import sys; print("ready", flush=True); sys.stdin.read()'],
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(child.stdout.readline().strip(), 'ready')
            self.assertTrue(ProductionWorkflow._process_is_alive(child.pid))
            try:
                code = child.wait(timeout=0.3)
            except subprocess.TimeoutExpired:
                code = None
            self.assertIsNone(code, 'Liveness probe terminated a live process')
        finally:
            child.communicate(timeout=5)
        self.assertFalse(ProductionWorkflow._process_is_alive(child.pid))

    def test_invalid_pid(self):
        self.assertFalse(ProductionWorkflow._process_is_alive(0))
        self.assertFalse(ProductionWorkflow._process_is_alive(-1))
