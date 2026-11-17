import json
import sys
import tempfile
import unittest
from pathlib import Path
from pypdf import PdfWriter

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.schema.gate_result import gate_check, gate_result
from submission.gates.publish_gate import run_publish_gate, sha256_file


class PublishBindingTests(unittest.TestCase):
    def test_one_missing_document_attestation_blocks(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / 'source.docx'
            source.write_bytes(b'fixture')
            paths = []
            for name in ('scientific_gate', 'template_compliance_gate', 'artifact_integrity_gate'):
                report = gate_result(name, [gate_check('fixture', True)], run_id='r')
                if name != 'scientific_gate':
                    report['artifacts'] = {'docx_sha256': sha256_file(source)}
                path = root / (name + '.json')
                path.write_text(json.dumps(report))
                paths.append(path)
            self.assertEqual('FAIL', run_publish_gate('r', paths, source, root / 'out.docx')['status'])


class PdfPageTests(unittest.TestCase):
    def test_page_limits_binding_and_missing_boundary(self):
        from submission.gates.pdf_page_gate import check_pdf_pages
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / 'paper.pdf'
            writer = PdfWriter()
            for _ in range(34):
                writer.add_blank_page(width=595, height=842)
            writer.write(path)
            boundary = {'pdf_sha256': sha256_file(path), 'abstract_end': 1,
                        'body_end': 31, 'reviewer': 'fixture', 'status': 'APPROVED'}
            self.assertEqual('PASS', check_pdf_pages('r', path, boundary)['status'])
            boundary['body_end'] = 32
            self.assertEqual('FAIL', check_pdf_pages('r', path, boundary)['status'])
            boundary['body_end'] = 31
            boundary['pdf_sha256'] = 'stale'
            self.assertEqual('FAIL', check_pdf_pages('r', path, boundary)['status'])
            self.assertEqual('FAIL', check_pdf_pages('r', path, {})['status'])
            self.assertEqual('FAIL', check_pdf_pages('r', path.with_name('missing.pdf'), {})['status'])
