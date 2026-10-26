"""One finite Windows preparation pass. SDK libraries never enter the artifact."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess
from prepare_original_assets import inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=Path('preparation-sources.json'))
    parser.add_argument('--plan', action='store_true')
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    inputs(manifest)
    if args.plan:
        print(json.dumps({'trees': len(manifest['trees']), 'gr2': len(manifest['gr2']),
                          'childTimeoutSeconds': 12, 'executions': False}))
        return
    if os.name != 'nt':
        raise RuntimeError('SDK preparation is Windows-only; not executed on the local machine')
    results = []
    for kind, rows in [('trees', manifest['trees']), ('gr2', manifest['gr2'])]:
        for row in rows:
            dest = Path('outputs')/('baked' if kind == 'trees' else 'repaired')/Path(row['target']).name
            dest.parent.mkdir(parents=True, exist_ok=True)
            command = [str(Path('bake_spt.exe').resolve()), row['target'], str(dest)] if kind == 'trees' else [str(Path('repair_gr2.exe').resolve()), str(Path('gran211.dll').resolve()), row['target'], str(dest)]
            entry = {'source': row['path'], 'inputSha256': row['sha256'], 'kind': kind}
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=12)
                if kind == 'gr2' and result.returncode == 2:
                    shutil.copyfile(row['target'], dest)
                elif result.returncode:
                    raise RuntimeError((result.stderr or result.stdout)[-1500:])
                raw = dest.read_bytes()
                if kind == 'trees':
                    if raw[:8] != b'TMP4SPT1':
                        raise ValueError('Unexpected baked tree format')
                else:
                    if raw[:16] != bytes.fromhex('b867b0caf86db10f84728c7e5e19001e'):
                        raise ValueError('Unexpected GR2 magic')
                    table, count = struct.unpack_from('<II', raw, 44)
                    for index in range(count):
                        compression, offset, size, expanded = struct.unpack_from('<IIII', raw, 32+table+index*44)
                        if compression or size != expanded or offset+size > len(raw):
                            raise ValueError('Repacked GR2 is not complete uncompressed data')
                entry.update(state='prepared-awaiting-local-verification', output=dest.as_posix(),
                             bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
            except Exception as error:
                dest.unlink(missing_ok=True)
                entry.update(state='failed', error=type(error).__name__+': '+str(error))
            results.append(entry)
            Path('outputs/results.json').write_text(json.dumps({'schema': 1,
                'run': os.environ.get('GITHUB_RUN_ID'), 'commit': os.environ.get('GITHUB_SHA'),
                'results': results}, indent=2)+'\n')
    if any(row['state'] == 'failed' for row in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
