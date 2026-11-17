"""Count a real PDF, with explicit reviewed section boundaries; never infer layout.

Electronic CUMCM 2026 profile: abstract first, body <=30 pages, appendices
excluded. The one-page abstract guideline is conservatively enforced locally.
This gate does not verify semantic boundaries, typography or visual quality.
"""
import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from core.schema.gate_result import gate_check, gate_result, write_gate_result

RULE_SOURCE = 'https://www.mcm.edu.cn/html_cn/node/4cd596519c9eb9fbd866398f6df0caa3.html'


def check_pdf_pages(run_id, pdf, boundaries):
    checks, artifacts = [], {}
    try:
        from pypdf import PdfReader
        data = Path(pdf).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        reader = PdfReader(BytesIO(data), strict=True)
        if reader.is_encrypted:
            raise ValueError('ENCRYPTED_PDF')
        total = len(reader.pages)
        artifacts = {'pdf_sha256': digest, 'total_pages': total}
        checks.append(gate_check('PDF readable and nonempty', total > 0))
        valid = (isinstance(boundaries, dict) and boundaries.get('pdf_sha256') == digest
                 and boundaries.get('status') == 'APPROVED'
                 and isinstance(boundaries.get('reviewer'), str) and bool(boundaries['reviewer'].strip())
                 and type(boundaries.get('abstract_end')) is int
                 and type(boundaries.get('body_end')) is int)
        checks.append(gate_check('reviewed boundaries bound to PDF', bool(valid)))
        if valid:
            abstract, end = boundaries['abstract_end'], boundaries['body_end']
            checks.extend([
                gate_check('electronic abstract occupies first page', abstract == 1),
                gate_check('contiguous body range within PDF', 1 <= abstract < end <= total),
                gate_check('body page limit', 1 <= end - abstract <= 30,
                           actual=end - abstract, expected='1..30'),
            ])
    except Exception as exc:
        checks.append(gate_check('PDF readable', False, message=type(exc).__name__))
    report = gate_result('pdf_page_gate', checks, run_id=run_id)
    report.update(artifacts=artifacts, rule_source=RULE_SOURCE,
                  scope='Page arithmetic only; human boundary and visual review remain required.')
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--pdf', required=True)
    parser.add_argument('--boundaries', required=True)
    parser.add_argument('--report', required=True)
    args = parser.parse_args()
    try:
        boundaries = json.loads(Path(args.boundaries).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        boundaries = {}
    report = check_pdf_pages(args.run_id, args.pdf, boundaries)
    write_gate_result(args.report, report)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
