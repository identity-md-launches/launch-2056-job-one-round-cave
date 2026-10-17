#!/usr/bin/env python3
"""Offline, bounded comparison of explicit OpenAPI discriminator dispatch targets."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('dispatchcheck_previous',
    Path(__file__).resolve().parents[1] / 'fallbackheaders/fallbackheaders.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
api = previous.api
MAX_MAPPING = 64
MAX_DISPATCH_PAIRS = 512


def dispatch(document, schema):
    """Validate explicit mappings without fetching or inventing implicit routes."""
    if 'discriminator' not in schema:
        return None
    raw = schema['discriminator']
    api.require(isinstance(raw, dict), 'discriminator must be an object')
    api.require(isinstance(raw.get('propertyName'), str) and raw['propertyName'],
                'discriminator propertyName must be a nonempty string')
    api.require(all(k in {'propertyName', 'mapping'} or k.startswith('x-') for k in raw),
                'unsupported discriminator field')
    composites = set(schema) & {'oneOf', 'anyOf', 'allOf'}
    api.require(composites, 'discriminator needs oneOf, anyOf or allOf')
    for key in composites:
        api.require(isinstance(schema[key], list) and schema[key],
                    key + ' must be a nonempty array')
    mapping = raw.get('mapping', {})
    api.require(isinstance(mapping, dict) and len(mapping) <= MAX_MAPPING,
                'discriminator mapping must be an object of at most 64 entries')
    targets = {}
    components = document.obj.get('components', {})
    schemas = components.get('schemas', {}) if isinstance(components, dict) else {}
    for tag, value in sorted(mapping.items()):
        api.require(isinstance(tag, str) and isinstance(value, str) and value,
                    'discriminator mapping keys and targets must be strings; target cannot be empty')
        if value.startswith('#/'):
            ref = value
        else:
            api.require(isinstance(schemas, dict) and value in schemas,
                        'mapping target must be a local pointer or an existing component schema name; '
                        'remote targets are never fetched: ' + value)
            ref = api.pointer('/components/schemas', value)
            ref = '#' + ref
        target = document.resolve({'$ref': ref})
        api.require(isinstance(target, (dict, bool)), 'dispatch target must resolve to a schema')
        targets[tag] = (ref, target)
    return raw, targets


class Analyzer(previous.Analyzer):
    def __init__(self, old, new):
        super().__init__(old, new)
        self.dispatch_pairs = []

    def schema(self, old, new, loc, direction):
        # Unlike the original equality shortcut, walk equal inline containers:
        # mapping strings are references without a literal "$ref" field.
        self.steps += 1
        api.require(self.steps <= api.MAX_STEPS, 'schema comparison limit exceeded')
        old, new = self.old.resolve(old), self.new.resolve(new)
        api.require(isinstance(old, (dict, bool)) and isinstance(new, (dict, bool)),
                    'schema must be an object or boolean')
        if type(old) is bool or type(new) is bool:
            self.changed(old, new, loc, 'boolean_schema_changed',
                         'Boolean schema changed; review accepted values.')
            return
        pair = (id(old), id(new), direction)
        if pair in self.active:
            return
        self.active.add(pair)
        try:
            self._schema(old, new, loc, direction)
        finally:
            self.active.remove(pair)

    def _schema(self, old, new, loc, direction):
        super()._schema(old, new, loc, direction)
        before, after = dispatch(self.old, old), dispatch(self.new, new)
        if before is None and after is None:
            return
        base = loc + '/discriminator'
        if before is None or after is None:
            self.emit('review', 'discriminator_presence_changed', base,
                      'Dispatch hint added or removed; check generated serializers and deserializers.')
            return
        a, am = before
        b, bm = after
        if a['propertyName'] != b['propertyName']:
            self.emit('review', 'discriminator_property_changed', base + '/propertyName',
                      'Dispatch property changed; old clients may read or send a different tag field.')
            return
        if not am or not bm:
            self.emit('review', 'discriminator_implicit_dispatch_unchecked', base + '/mapping',
                      'At least one mapping is empty or omitted; implicit schema-name dispatch is not inferred.')
        for tag in sorted(am.keys() | bm.keys()):
            tloc = api.pointer(base + '/mapping', tag)
            if tag not in bm or tag not in am:
                self.emit('review', 'discriminator_mapping_removed' if tag not in bm else
                          'discriminator_mapping_added', tloc,
                          'Explicit tag coverage changed; implicit routes and actual payload reachability need review.')
                continue
            ar, av = am[tag]
            br, bv = bm[tag]
            if ar != br:
                self.emit('review', 'discriminator_target_changed', tloc,
                          'This tag points to a different local schema; check generated type selection.')
            api.require(len(self.dispatch_pairs) < MAX_DISPATCH_PAIRS,
                        'dispatch pair limit exceeded; compare a smaller description')
            self.dispatch_pairs.append(dict(location=tloc, tag=tag, direction=direction,
                                            old_target=ar, new_target=br))
            # The /target suffix is a virtual location: the string at mapping/tag
            # identifies the compared schemas, rather than containing them inline.
            self.schema(av, bv, tloc + '/target', direction)


def compare(old, new):
    analyzer = Analyzer(old, new)
    report = analyzer.run()
    report.update(extension='dispatchcheck-v1 (includes fallbackheaders and earlier analyzers)',
                  dispatch_pairs=analyzer.dispatch_pairs,
                  schema_visits=analyzer.steps,
                  selector_groups=analyzer.selector_groups,
                  status_visits=analyzer.status_visits,
                  remapped_header_pairs=analyzer.remapped_header_pairs,
                  dispatch_scope='Explicit common tags with equal propertyName; local targets only. '
                                 'Target constraint findings are potential branch-level breaks, not '
                                 'proof of whole-union incompatibility. Implicit dispatch, union '
                                 'satisfiability and unmatched branches are not inferred.')
    return report


def demo():
    capture = Path(__file__).resolve().parents[1] / 'apidelta/imd-openapi.json'
    old, digest = api.load(capture)
    old = copy.deepcopy(old)
    path = sorted(old['paths'])[0]
    method = sorted(old['paths'][path].keys() & api.METHODS)[0]
    schemas = old.setdefault('components', {}).setdefault('schemas', {})
    api.require('DispatchExample36' not in schemas, 'demo component collides with capture')
    schemas['DispatchExample36'] = {'type': 'object', 'required': ['kind', 'receipt'],
        'properties': {'kind': {'type': 'string', 'enum': ['done']},
                       'receipt': {'type': 'string'}}}
    union = {'oneOf': [{'$ref': '#/components/schemas/DispatchExample36'}],
             'discriminator': {'propertyName': 'kind',
                 'mapping': {'done': '#/components/schemas/DispatchExample36'}}}
    old['paths'][path][method]['responses'] = {'200': {'description': 'Hypothetical dispatch',
        'content': {'application/json': {'schema': union}}}}
    new = copy.deepcopy(old)
    new['components']['schemas']['DispatchExample36']['properties']['receipt']['type'] = 'integer'
    report = compare(old, new)
    api.require(any(f['code'] == 'schema_type_incompatible' and '/mapping/done/target/' in f['location']
                    for f in report['findings']), 'demo failed to compare unchanged mapping targets')
    report.update(capture_sha256=digest, baseline_source='https://api.imd.fun/openapi.json',
                  demo='Real saved IMD operation with hypothetical response dispatch. The mapping '
                       'is unchanged but receipt changes from string to integer in its target. '
                       'No described operation is called.')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('demo')
    diff = commands.add_parser('compare')
    diff.add_argument('old')
    diff.add_argument('new')
    args = parser.parse_args(argv)
    try:
        if args.command == 'demo':
            report = demo()
        else:
            old, oh = api.load(args.old)
            new, nh = api.load(args.new)
            report = compare(old, new)
            report.update(old_sha256=oh, new_sha256=nh)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0 if args.command == 'demo' else {
            'breaking': 1, 'review_required': 3, 'no_detected_breakage': 0}[report['status']]
    except (api.Invalid, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print('dispatchcheck: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
