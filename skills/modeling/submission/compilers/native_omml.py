"""Strict OMML writer for the polynomial LaTeX emitted by the checked math layer.

Unsupported syntax is an error, never a successful plain-text equation.
"""
import re

from docx.oxml import OxmlElement


def _run(text):
    run = OxmlElement('m:r')
    node = OxmlElement('m:t')
    node.text = text
    run.append(node)
    return run


def polynomial_omml(expression):
    if not isinstance(expression, str) or not expression.strip() or len(expression) > 8192:
        raise ValueError('OMML_EXPRESSION_INVALID')
    position = 0

    def group(depth):
        nonlocal position
        if position >= len(expression) or expression[position] != '{':
            raise ValueError('OMML_GROUP_REQUIRED')
        position += 1
        nodes = sequence(depth + 1, grouped=True)
        if not nodes:
            raise ValueError('OMML_EMPTY_GROUP')
        return nodes

    def sequence(depth=0, grouped=False):
        nonlocal position
        if depth > 16:
            raise ValueError('OMML_COMPLEXITY_LIMIT')
        nodes = []
        while position < len(expression):
            char = expression[position]
            if char.isspace():
                position += 1
                continue
            if char == '}':
                if not grouped:
                    raise ValueError('OMML_UNMATCHED_GROUP')
                position += 1
                return nodes
            if expression.startswith('\\frac', position):
                position += 5
                numerator, denominator = group(depth), group(depth)
                node = OxmlElement('m:f')
                for tag, children in (('m:num', numerator), ('m:den', denominator)):
                    part = OxmlElement(tag)
                    part.extend(children)
                    node.append(part)
            elif expression.startswith('\\mathrm{', position):
                match = re.match(r'\\mathrm\{([A-Za-z][A-Za-z0-9]*(?:(?:\\_)[A-Za-z0-9]+)*)\}', expression[position:])
                if not match:
                    raise ValueError('OMML_IDENTIFIER_INVALID')
                node = _run(match[1].replace('\\_', '_'))
                properties = OxmlElement('m:rPr')
                style = OxmlElement('m:sty')
                style.set('{http://schemas.openxmlformats.org/officeDocument/2006/math}val', 'p')
                properties.append(style)
                node.insert(0, properties)
                position += len(match[0])
            elif char in '+-=':
                node = _run('−' if char == '-' else char)
                position += 1
            elif char.isascii() and char.isalpha():
                node = _run(char)
                position += 1
            elif char.isascii() and char.isdigit():
                match = re.match(r'[0-9]+', expression[position:])
                node = _run(match[0])
                position += len(match[0])
            else:
                raise ValueError('OMML_SYNTAX_UNSUPPORTED')
            if position < len(expression) and expression[position] == '^':
                position += 1
                superscript = group(depth)
                power = OxmlElement('m:sSup')
                base, exponent = OxmlElement('m:e'), OxmlElement('m:sup')
                base.append(node)
                exponent.extend(superscript)
                power.extend([base, exponent])
                node = power
            nodes.append(node)
        if grouped:
            raise ValueError('OMML_UNCLOSED_GROUP')
        return nodes

    root = OxmlElement('m:oMath')
    root.extend(sequence())
    return root
