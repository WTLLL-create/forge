"""TimeoutExpired carries byte output even when subprocess uses text=True."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODELING = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(MODELING))
sys.path.insert(0, str(MODELING / 'tests/v8'))
from test_forge_v8 import make_trust_stages
from core.runtime.production_workflow import ProductionWorkflow


class StageTimeoutTests(unittest.TestCase):
    def test_timeout_with_partial_bytes_is_recorded_as_failure(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / 'source_inputs').mkdir()
            (root / 'source_inputs/source.txt').write_text('fixture')
            script = root / 'model.py'
            script.write_text('print("fixture")')
            config = {'schema': 'forge-project-workflow/v2', 'workflow_id': 'timeout-fixture',
                      'inputs': [{'kind': 'source', 'source': 'source_inputs/source.txt', 'target': 'source.txt'}],
                      'stages': make_trust_stages(script)}
            path = root / 'workflow.json'
            path.write_text(json.dumps(config))
            workflow = ProductionWorkflow(path)
            workflow.prepare()
            try:
                failure = subprocess.TimeoutExpired('synthetic', 1, output=b'partial stdout', stderr=b'partial stderr')
                with patch('core.runtime.production_workflow.subprocess.run', side_effect=failure):
                    self.assertFalse(workflow._run_stage(config['stages'][0]))
                self.assertIn('timed out', (workflow.current_run / 'logs/model_compute.stderr.log').read_text())
                self.assertEqual(124, workflow.manifest['stages'][-1]['returncode'])
            finally:
                workflow._release_lock()
