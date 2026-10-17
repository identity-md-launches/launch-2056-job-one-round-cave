#!/usr/bin/env python3
"""Show a changed discriminator target inside two approved, inert ZIP snapshots."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

import api_bundle


def documents():
    capture = Path(__file__).with_name('imd-openapi.json').read_bytes()
    old = json.loads(capture)
    operation = old['paths']['/requests/quote']['post']
    old.setdefault('components', {}).setdefault('schemas', {})['DispatchExample'] = {
        'type': 'object', 'required': ['kind', 'receipt'],
        'properties': {'kind': {'type': 'string', 'enum': ['done']},
                       'receipt': {'type': 'string'}}}
    operation['responses'] = {'200': {'description': 'Illustrative response',
        'content': {'application/json': {'schema': {
            'oneOf': [{'$ref': '#/components/schemas/DispatchExample'}],
            'discriminator': {'propertyName': 'kind',
                'mapping': {'done': '#/components/schemas/DispatchExample'}}}}}}}
    new = copy.deepcopy(old)
    new['components']['schemas']['DispatchExample']['properties']['receipt']['type'] = 'integer'
    return capture, old, new


def demo():
    capture, old, new = documents()
    scratch = Path('test/scratch')
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dispatch-bundle-', dir=scratch) as folder:
        paths, digests = [], []
        for name, document in (('old', old), ('new', new)):
            path = Path(folder) / (name + '.zip')
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr(zipfile.ZipInfo('docs/openapi.json'), json.dumps(document))
            paths.append(path)
            digests.append(hashlib.sha256(path.read_bytes()).hexdigest())
        options = dict(member='docs/openapi.json', old_sha256=digests[0],
                       new_sha256=digests[1], seconds=10)
        earlier = api_bundle.compare(*paths, fallback_headers=True, **options)
        changed = api_bundle.compare(*paths, dispatch=True, **options)
        unchanged = api_bundle.compare(paths[0], paths[0], dispatch=True,
            member=options['member'], old_sha256=digests[0], new_sha256=digests[0])
        assert earlier['status'] == 'review_required'
        assert changed['status'] == 'breaking' and len(changed['dispatch_pairs']) == 1
        assert any(f['code'] == 'schema_type_incompatible' and
                   '/mapping/done/target/' in f['location'] for f in changed['findings'])
        assert unchanged['status'] == 'no_detected_breakage' and not unchanged['findings']
        assert len(list(Path(folder).iterdir())) == 2
        return dict(baseline_source='https://api.imd.fun/openapi.json',
            capture_sha256=hashlib.sha256(capture).hexdigest(),
            trial='Hypothetical dispatch target on a saved IMD operation changes receipt from string to integer while its tag and mapping stay the same.',
            network_used=False, extracted_files=0,
            earlier_mode_result=earlier['status'], unchanged_result=unchanged['status'],
            changed=changed)


if __name__ == '__main__':
    print(json.dumps(demo(), indent=2))
