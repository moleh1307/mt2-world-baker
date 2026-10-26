"""Download only the exact public files in a reviewed, hash-pinned manifest."""
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from urllib.request import urlopen
import argparse
import hashlib
import json
import re


def inputs(manifest):
    rows = manifest['sdk']+manifest['trees']+manifest['gr2']
    if not 0 < len(rows) <= 64 or manifest['schema'] != 1:
        raise ValueError('Invalid bounded input manifest')
    targets = set()
    for row in rows:
        if row['repo'] not in {'https://github.com/d1str4ught/m2dev-client',
                               'https://github.com/Metin2Learn/ymir-work',
                               'https://github.com/NakiuS/Metin2Client'}:
            raise ValueError('Unapproved source repository')
        if not re.fullmatch('[a-f0-9]{40}', row['commit']) or not re.fullmatch('[a-f0-9]{40}', row['gitBlob']):
            raise ValueError('Source must be pinned to a full commit and Git blob')
        if not re.fullmatch('[a-f0-9]{64}', row['sha256']) or not 0 < row['bytes'] < 8_000_000:
            raise ValueError('Invalid source hash or size')
        for key in ['path', 'target']:
            value = row[key]
            if '\\' in value or ':' in value or PurePosixPath(value).is_absolute() or '..' in PurePosixPath(value).parts:
                raise ValueError('Input paths must be relative and contained')
        if row['target'] in targets:
            raise ValueError('Duplicate input destination')
        targets.add(row['target'])
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('preparation-sources.json'))
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    rows = inputs(manifest)
    if args.plan:
        print(json.dumps({'inputs': len(rows), 'trees': len(manifest['trees']),
                          'gr2': len(manifest['gr2']), 'bytes': sum(r['bytes'] for r in rows),
                          'downloads': False, 'executions': False}))
        return
    for row in rows:
        url = row['repo'].replace('github.com', 'raw.githubusercontent.com')+'/'+row['commit']+'/'+quote(row['path'])
        raw = urlopen(url, timeout=30).read()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256'] or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest() != row['gitBlob']:
            raise ValueError('Pinned input integrity: '+row['path'])
        dest = Path(row['target'])
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(raw)
        print(row['target'], row['sha256'])
    Path('outputs').mkdir(exist_ok=True)
    Path('outputs/input-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
