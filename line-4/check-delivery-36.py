#!/usr/bin/env python3
"""Independent stdlib checks of round 36 media, preservation, records and scope."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib


def git(*args):
    return subprocess.check_output(['git', *args])


def png_pixels(raw):
    assert raw[:8] == b'\x89PNG\r\n\x1a\n'
    offset, parts = 8, []
    width = height = channels = None
    while offset < len(raw):
        size = int.from_bytes(raw[offset:offset+4], 'big')
        kind, data = raw[offset+4:offset+8], raw[offset+8:offset+8+size]
        assert zlib.crc32(kind+data) == int.from_bytes(raw[offset+8+size:offset+12+size], 'big')
        if kind == b'IHDR':
            width, height, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', data)
            assert (width, height, depth, compression, filtering, interlace) == (1254,1254,8,0,0,0)
            assert color in (2,6)
            channels = 3 if color == 2 else 4
        if kind == b'IDAT':
            parts.append(data)
        offset += size+12
        if kind == b'IEND':
            assert offset == len(raw)
            break
    stride = width*channels
    filtered = zlib.decompress(b''.join(parts))
    assert len(filtered) == (stride+1)*height
    decoded = bytearray(stride*height)
    for y in range(height):
        row = y*(stride+1)
        mode = filtered[row]
        assert mode <= 4
        for x in range(stride):
            at = y*stride+x
            a = decoded[at-channels] if x >= channels else 0
            b = decoded[at-stride] if y else 0
            c = decoded[at-stride-channels] if y and x >= channels else 0
            p = a+b-c
            distances = abs(p-a), abs(p-b), abs(p-c)
            paeth = (a,b,c)[distances.index(min(distances))]
            predicted = (0,a,b,(a+b)//2,paeth)[mode]
            decoded[at] = (filtered[row+1+x]+predicted)&255
    if channels == 4:
        assert all(decoded[i] == 255 for i in range(3,len(decoded),4))
        decoded = bytearray(v for i,v in enumerate(decoded) if i%4 != 3)
    return decoded


def jpeg_dimensions(raw):
    assert raw[:2] == b'\xff\xd8' and raw[-2:] == b'\xff\xd9'
    p = 2
    while p < len(raw):
        assert raw[p] == 255
        while raw[p] == 255:
            p += 1
        marker = raw[p]
        p += 1
        length = int.from_bytes(raw[p:p+2], 'big')
        if marker in (0xC0,0xC1,0xC2):
            height,width = struct.unpack('>HH', raw[p+3:p+7])
            return width,height
        assert length >= 2
        p += length
    raise AssertionError('no JPEG dimensions')


def main():
    path = Path('artifacts/line-4/wall-v17.png')
    wall = path.read_bytes()
    assert wall == Path('artifacts/line-4/wall.png').read_bytes()
    assert git('ls-files','--',str(path)) == b'', 'named output must stay untracked'
    before = Path('artifacts/line-4/wall-v16.png').read_bytes()
    prior = json.loads(Path('dist/line-4/35.json').read_text())
    assert prior['image'].endswith(hashlib.sha256(before).hexdigest())
    old,new = png_pixels(before),png_pixels(wall)
    changed = outside = 0
    for y in range(1254):
        for x in range(1254):
            p=(y*1254+x)*3
            if old[p:p+3] != new[p:p+3]:
                changed += 1
                outside += not (650 <= x < 800 and 170 <= y < 290)
    assert changed == 2608 and outside == 0
    record = json.loads(Path('dist/line-4/36.json').read_text())
    assert set(record) == {'name','image','attributes'}
    assert record['image'] == 'https://api.imd.fun/artifacts/'+hashlib.sha256(wall).hexdigest()
    attrs = record['attributes']
    assert all(set(a) == {'trait_type','value'} for a in attrs)
    assert [a['trait_type'] for a in attrs] == ['Cave','Wall','Number','Left behind','Meaning','One thing']
    assert [a['value'] for a in attrs[:4]] == ['Lava','Line 4',36,'DispatchCheck']
    assert type(attrs[2]['value']) is int
    assert len(list(Path('dist/line-4').glob('[0-9][0-9].json'))) == 36
    preview = Path('dist/line-4/36.jpg').read_bytes()
    assert preview == Path('artifacts/line-4/36.jpg').read_bytes()
    assert jpeg_dimensions(preview) == (512,512) and len(preview) < 100000
    # Byte-check all ancestral records, previews and tool/goal/media files.
    tracked = git('ls-tree','-r','--name-only','HEAD','--','line-4','dist/line-4','artifacts/line-4').decode().splitlines()
    mutable = {'line-4/README.md','line-4/USED.md','artifacts/line-4/wall.png'}
    for name in tracked:
        if name not in mutable:
            assert Path(name).read_bytes() == git('show','HEAD:'+name), name
    paths = set(git('diff','--name-only','HEAD').decode().splitlines())
    paths.update(git('ls-files','--others','--exclude-standard').decode().splitlines())
    assert all(p.startswith(('line-4/','dist/line-4/','artifacts/line-4/','test/scratch/')) for p in paths), paths
    for name in paths:
        p=Path(name)
        if p.is_file() and not name.startswith(('artifacts/','test/scratch/')):
            assert p.stat().st_size <= 100000, name
    results = json.loads(Path('line-4/check-results-36.json').read_text())
    assert len(results['suites']) == 16 and all(s['exit'] == 0 for s in results['suites'])
    assert sum(s['tests'] for s in results['suites']) == 250
    assert results['live']['matches_capture'] and not results['live']['comparison']['findings']
    review = json.loads(Path('line-4/review-36.json').read_text())
    assert review['sha256'] == hashlib.sha256(wall).hexdigest()
    assert review['dimensions'] == [1254,1254] and review['pixels_changed_outside_addition'] == outside
    assert review['format'] == 'RGB PNG' and 'unmet_visual_requirements' in review
    result = dict(status='passed', number=36, ancestral_files_byte_identical=len(tracked)-len(mutable),
                  goal_unchanged=True, scope_passed=True, size_limits_passed=True,
                  suites_passed=16, tests_passed=250, changed_pixels=changed,
                  pixels_changed_outside_addition=outside, wall_dimensions=[1254,1254],
                  wall_format='RGB PNG', wall_bytes=len(wall),preview_dimensions=[512,512],
                  preview_format='JPEG',preview_bytes=len(preview),sha256=hashlib.sha256(wall).hexdigest())
    Path('line-4/delivery-check-36.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
