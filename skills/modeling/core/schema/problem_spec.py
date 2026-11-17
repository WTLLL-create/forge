"""ProblemSpec v1 and validation of its deliberately small JSON Schema subset."""
from core.schema.gate_result import gate_check, gate_result


def obj(**fields):
    return {'type': 'object', 'properties': fields, 'required': list(fields), 'additionalProperties': False}


def array(items, minimum=0):
    return {'type': 'array', 'items': items, 'minItems': minimum}


TEXT = {'type': 'string', 'minLength': 1}
SOURCE = obj(asset_id=TEXT, sha256=TEXT, locator=TEXT, quote=TEXT)
SOURCES = array(SOURCE, 1)
STATEMENT = obj(text=TEXT, sources=SOURCES)
UNCERTAINTY = obj(id=TEXT, description=TEXT, sources=SOURCES)
PROBLEM_SPEC_SCHEMA = obj(
    problem_id=TEXT, background=array(STATEMENT),
    questions=array(obj(id=TEXT, task=TEXT, objective=TEXT, sources=SOURCES,
                        required_outputs=array(STATEMENT, 1)), 1),
    data_assets=array(obj(id=TEXT, role=TEXT, question_ids=array(TEXT), sources=SOURCES,
                          certainty={'type': 'string', 'enum': ['explicit', 'inferred', 'unknown']})),
    constraints=array(STATEMENT), evaluation_criteria=array(STATEMENT),
    ambiguities=array(UNCERTAINTY), assumptions_requiring_confirmation=array(UNCERTAINTY),
)


def _shape(value, schema):
    kind = schema['type']
    if kind == 'object':
        if not isinstance(value, dict) or set(value) != set(schema['required']):
            raise ValueError('SCHEMA_FIELDS_INVALID')
        for key, field in schema['properties'].items():
            _shape(value[key], field)
    elif kind == 'array':
        if not isinstance(value, list) or len(value) < schema.get('minItems', 0):
            raise ValueError('SCHEMA_ARRAY_INVALID')
        for item in value:
            _shape(item, schema['items'])
    elif kind == 'string':
        if not isinstance(value, str) or not value.strip():
            raise ValueError('SCHEMA_STRING_INVALID')
        if 'enum' in schema and value not in schema['enum']:
            raise ValueError('SCHEMA_ENUM_INVALID')
    else:
        raise ValueError('UNSUPPORTED_SCHEMA_KEYWORD')


def _sources(value):
    if isinstance(value, dict):
        if set(value) == {'asset_id', 'sha256', 'locator', 'quote'}:
            yield value
        else:
            for child in value.values():
                yield from _sources(child)
    elif isinstance(value, list):
        for child in value:
            yield from _sources(child)


def validate_problem_spec(spec, package):
    checks = []
    try:
        _shape(spec, PROBLEM_SPEC_SCHEMA)
        checks.append(gate_check('schema_shape', True))
        assets = {a['id']: a for a in package['content']['assets']}
        checks.append(gate_check('problem_identity', spec['problem_id'] == package['content']['problem_id']))
        questions = [q['id'] for q in spec['questions']]
        checks.append(gate_check('unique_question_ids', len(set(questions)) == len(questions)))
        for n, source in enumerate(_sources(spec)):
            asset = assets.get(source['asset_id'], {})
            line = asset.get('segments', {}).get(source['locator'], '')
            checks.append(gate_check(f'evidence_{n}', source['sha256'] == asset.get('sha256') and source['quote'] in line))
        declared = [a['id'] for a in spec['data_assets']]
        checks.append(gate_check('all_attachments_accounted_for', len(declared) == len(set(declared)) and set(declared) == set(assets) - {'statement'}))
        for asset in spec['data_assets']:
            checks.append(gate_check('attachment_question_links', set(asset['question_ids']) <= set(questions)))
            if assets.get(asset['id'], {}).get('inspection') == 'opaque':
                checks.append(gate_check('opaque_attachment_not_claimed_understood', asset['certainty'] != 'explicit' and bool(spec['ambiguities'])))
            if asset['certainty'] != 'explicit':
                checks.append(gate_check('inferred_role_requires_uncertainty', bool(spec['ambiguities'] or spec['assumptions_requiring_confirmation'])))
    except (ValueError, KeyError, TypeError):
        checks.append(gate_check('SCHEMA_INVALID', False, message='ProblemSpec schema validation failed'))
    return gate_result('problem_schema_evidence', checks, run_id=package['meta']['run_id'])
