"""Structural tests for native fractions/powers and strict rejection."""
from pathlib import Path
import sys
import unittest
import tempfile
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from submission.compilers.native_omml import polynomial_omml
from core.schema.polynomial_math import checked_expression, latex

def query(node, path):
    return node.xpath(path, namespaces={'m': 'http://schemas.openxmlformats.org/officeDocument/2006/math'})


class NativeMathTests(unittest.TestCase):
    def test_compiler_inserts_native_math_and_blocks_invalid_input_before_save(self):
        from docx import Document
        from docx.document import Document as DocumentClass
        from submission.compilers.template_docx_compiler import compile_markdown
        root = Path(__file__).resolve().parents[2]
        template = root / 'submission/templates/CUMCM_template.docx'
        contract = root / 'submission/templates/cumcm_template.json'
        for text, valid in ((r'$$\frac{1}{3} x^{2}$$', True),
                            ('$$\nx^{2}', False), (r'$$\sqrt{x}$$', False)):
            with self.subTest(text=text), tempfile.TemporaryDirectory(prefix='codex-omml-test-') as raw:
                source = Path(raw) / 'source.md'
                source.write_text('# Equation check\n\n' + text, encoding='utf-8')
                document = Document(template)
                with patch('submission.compilers.template_docx_compiler.Document', return_value=document), \
                     patch.object(DocumentClass, 'save') as save:
                    if valid:
                        result = compile_markdown(source, Path(raw) / 'candidate.docx', template, contract)
                        self.assertEqual(1, result['equations'])
                        self.assertEqual(1, len(document._element.xpath('.//m:oMath')))
                        self.assertEqual(1, len(document._element.xpath('.//m:f')))
                        save.assert_called_once()
                    else:
                        with self.assertRaises(ValueError):
                            compile_markdown(source, Path(raw) / 'candidate.docx', template, contract)
                        save.assert_not_called()

    def test_fraction_and_power_are_native_nodes(self):
        node = polynomial_omml(r'\frac{1}{3} x^{2} - 2 x')
        self.assertEqual(1, len(query(node, './/m:f')))
        self.assertEqual(1, len(query(node, './/m:sSup')))
        self.assertEqual(['1'], query(node, './/m:num//m:t/text()'))
        self.assertEqual(['3'], query(node, './/m:den//m:t/text()'))
        self.assertEqual(['2'], query(node, './/m:sup//m:t/text()'))
        self.assertNotIn('\\frac', ''.join(query(node, './/m:t/text()')))

    def test_checked_polynomial_output_is_supported(self):
        for expression in ('(x-a)**2', 'x/3', '0', '-x', '2*x-2*a'):
            value = checked_expression(expression, {'x': '1', 'a': '1'})
            node = polynomial_omml(latex(value['polynomial']))
            self.assertTrue(query(node, './/m:t'))

    def test_named_symbol_is_literal_upright_math(self):
        node = polynomial_omml(r'\mathrm{target\_a}^{2}')
        self.assertEqual(['target_a', '2'], query(node, './/m:t/text()'))
        self.assertEqual(1, len(query(node, './/m:sty')))

    def test_unsupported_or_malformed_math_fails(self):
        for text in ('', r'\sqrt{x}', r'\frac{1}', 'x^{2', 'x}', r'\input{secret}',
                     r'\mathrm{a}{x}', 'x_1', '<script>', 'x**2', 'x^2'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                polynomial_omml(text)


if __name__ == '__main__':
    unittest.main()
