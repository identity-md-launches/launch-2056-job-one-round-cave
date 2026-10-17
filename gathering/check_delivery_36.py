#!/usr/bin/env python3
"""Verify gathering 36 bytes, records, local checks and path scope."""
import hashlib
import json
from pathlib import Path
import re
import subprocess

from check_delivery_35 import Gallery, GROUPS, jpeg, png, read_json, sha

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True,
                          check=True).stdout


def main():
    wall = ROOT / 'artifacts/gathering/wall-v17.png'
    previous = ROOT / 'artifacts/gathering/wall-v16.png'
    record = read_json('dist/gathering/36.json')
    assert set(record) == {'name', 'image', 'attributes'}
    assert len(record['attributes']) == 6
    attrs = {item['trait_type']: item['value'] for item in record['attributes']}
    assert set(attrs) == {'Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing'}
    assert (attrs['Cave'], attrs['Wall'], attrs['Number'], attrs['One thing']) == (
        'Lava', 'Gathering', 36, 'Gathering')
    assert type(attrs['Number']) is int
    assert record['image'] == 'https://api.imd.fun/artifacts/' + sha(wall.read_bytes())
    dimensions, pixels = png(wall)
    old_dimensions, old_pixels = png(previous)
    assert dimensions == old_dimensions == [1254, 1254]
    assert read_json('dist/gathering/35.json')['image'].endswith(sha(previous.read_bytes()))
    preservation = read_json('gathering/preservation-36.json')
    assert preservation['previous_sha256'] == sha(previous.read_bytes())
    assert preservation['wall_sha256'] == sha(wall.read_bytes())
    left, top, width, height = preservation['mark_rectangle']
    changed = outside = 0
    for y in range(dimensions[1]):
        for x in range(dimensions[0]):
            i = (y * dimensions[0] + x) * 3
            if pixels[i:i+3] != old_pixels[i:i+3]:
                changed += 1
                if not (left <= x < left+width and top <= y < top+height):
                    outside += 1
    assert changed == preservation['changed_pixels'] > 500
    assert outside == preservation['pixels_changed_outside'] == 0
    assert (ROOT / 'artifacts/gathering/wall.png').read_bytes() == wall.read_bytes()
    preview = ROOT / 'dist/gathering/36.jpg'
    thumb_dimensions = jpeg(preview)
    assert read_json('dist/goals.json') == [
        {'line': n, 'goal': (ROOT / f'line-{n}/GOAL.md').read_text().strip()}
        for n in range(1, 5)]
    page = (ROOT / 'dist/index.html').read_text()
    assert record['name'] in page
    parser = Gallery()
    parser.feed(page)
    assert parser.sections == GROUPS
    expected, painted, placeholders = [], 0, 0
    for folder in GROUPS:
        for path in sorted((ROOT / 'dist' / folder).glob('[0-9][0-9].json'), reverse=True):
            item = json.loads(path.read_text())
            expected.append(folder + '/' + path.name)
            assert re.fullmatch(r'https://api\.imd\.fun/artifacts/[0-9a-f]{64}', item['image'])
            if item['name'] == 'Not painted yet':
                placeholders += 1
                assert not path.with_suffix('.jpg').exists()
            else:
                painted += 1
        actual = [p for p in parser.records if p.startswith(folder + '/') and
                  read_json('dist/' + p)['name'] != 'Not painted yet']
        assert actual == sorted(actual, reverse=True)
    assert sorted(parser.records) == sorted(expected)
    for target, info in read_json('shared/api_bundle/SOURCES.json').items():
        assert sha((ROOT / 'shared/api_bundle' / target).read_bytes()) == info['sha256']
        assert sha((ROOT / info['source']).read_bytes()) == info['source_sha256']
    audit = read_json('gathering/audit-lines-36.json')
    assert len(audit['commands']) == 114 and all(row['passed'] for row in audit['commands'])
    assert sum(row['unittest_cases'] for row in audit['commands']) == 768
    shared = read_json('gathering/shared-check-results-36.json')
    assert shared['passed'] and shared['tests'] == 85 and shared['demos'] == 6
    assert len(shared['in_place']) == len(shared['standalone']) == 11
    review = read_json('gathering/review-36.json')
    assert review['wall_sha256'] == sha(wall.read_bytes())
    assert review['visual_requirements_unmet'] == []
    assert (ROOT / 'gathering/COINS.md').read_text().startswith('none\n')
    assert (ROOT / 'gathering/REPORT.md').stat().st_size > 1000
    changed_paths = set()
    for data in (git('diff', '--name-only', '-z', 'HEAD'),
                 git('ls-files', '--others', '--exclude-standard', '-z')):
        changed_paths.update(p.decode() for p in data.split(b'\0') if p)
    assert not any(p.startswith(('line-1/', 'line-2/', 'line-3/', 'line-4/'))
                   for p in changed_paths)
    for name in changed_paths:
        assert name.startswith(('gathering/', 'shared/', 'dist/', 'artifacts/gathering/',
                                'test/scratch/')), name
        path = ROOT / name
        if path.is_file() and not name.startswith(('artifacts/', 'test/scratch/')):
            assert path.stat().st_size <= 100000, name
    assert not git('ls-files', '--', 'artifacts/gathering/wall-v17.png')
    result = dict(passed=True, wall_sha256=sha(wall.read_bytes()),
        png_format='RGB PNG', png_dimensions=dimensions, png_bytes=wall.stat().st_size,
        jpeg_format='JPEG', jpeg_dimensions=thumb_dimensions, jpeg_bytes=preview.stat().st_size,
        records=len(expected), painted=painted, placeholders=placeholders,
        changed_pixels=changed, pixels_changed_outside=outside,
        line_folders_unchanged=True, checked_changed_paths=len(changed_paths),
        line_commands=114, line_unittest_cases=768, shared_tests=85,
        unmet_visual_requirements=[],
        visual_review='Manual inspection and byte preservation check; not independent certification.')
    (ROOT / 'gathering/delivery-check-36.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
