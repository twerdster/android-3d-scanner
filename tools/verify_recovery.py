#!/usr/bin/env python3
"""Offline archive-integrity and Android-resource checks; does not build/run the app."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(__file__).resolve().parents[1]
ANDROID = '{http://schemas.android.com/apk/res/android}'

def check_android(relative):
    base = ROOT / relative
    manifest = ET.parse(base / 'AndroidManifest.xml').getroot()
    package = manifest.attrib['package']
    declared = set()
    xml_count = 0
    for p in (base / 'res').rglob('*'):
        if not p.is_file():
            continue
        resource_type = p.relative_to(base / 'res').parts[0].split('-')[0]
        if resource_type != 'values':
            declared.add((resource_type, p.stem))
        if p.suffix == '.xml':
            xml_count += 1
            tree = ET.parse(p).getroot()
            if resource_type == 'values':
                for node in tree:
                    if node.get('name'):
                        declared.add((node.tag, node.get('name')))
            for node in tree.iter():
                for value in node.attrib.values():
                    if value.startswith('@+id/'):
                        declared.add(('id', value.split('/', 1)[1]))
    references = set()
    for p in base.rglob('*.java'):
        for kind, name in re.findall(r'(?<!android\.)\bR\.(\w+)\.(\w+)', p.read_text()):
            references.add((kind, name))
    missing = sorted(references - declared)
    activities = []
    java_root = base / ('java' if (base / 'java').is_dir() else 'src')
    for activity in manifest.findall('.//activity'):
        name = activity.get(ANDROID + 'name')
        full = package + name if name.startswith('.') else name if '.' in name else package + '.' + name
        path = java_root / (full.replace('.', '/') + '.java')
        assert path.is_file(), f'Missing declared activity: {relative}: {full}'
        activities.append(full)
    assert not missing, f'Unresolved local Java resources: {relative}: {missing}'
    return {'root': relative, 'manifest_package': package, 'activity_classes_present': activities,
            'xml_resource_files_parsed': xml_count, 'java_resource_references_resolved': len(references),
            'missing_local_java_resource_references': missing}

def inspect_image(path):
    data = path.read_bytes()
    if path.suffix == '.bmp':
        assert data[:2] == b'BM' and len(data) >= 54, str(path)
        width, height = struct.unpack_from('<ii', data, 18)
        assert width > 0 and height != 0
        assert struct.unpack_from('<I', data, 2)[0] == len(data)
        return {'format': 'BMP', 'width': width, 'height': abs(height)}
    assert data[:8] == b'\x89PNG\r\n\x1a\n', str(path)
    i = 8
    width = height = None
    while i < len(data):
        size = struct.unpack_from('>I', data, i)[0]
        kind = data[i + 4:i + 8]
        payload = data[i + 8:i + 8 + size]
        crc = struct.unpack_from('>I', data, i + 8 + size)[0]
        assert zlib.crc32(kind + payload) & 0xffffffff == crc, str(path)
        if kind == b'IHDR':
            width, height = struct.unpack_from('>II', payload)
        if kind == b'tEXt':
            key, value = payload.split(b'\0', 1)
            assert key in {b'date:create', b'date:modify'} and re.fullmatch(
                rb'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}', value
            ), f'Unreviewed PNG text: {path}'
        assert kind not in {b'zTXt', b'iTXt', b'eXIf'}, f'Unreviewed image metadata: {path}'
        i += size + 12
    assert i == len(data) and width and height
    return {'format': 'PNG', 'width': width, 'height': height}

def main():
    manifest = json.loads((ROOT / 'recovery/manifest.json').read_text())
    entries = manifest['files']
    paths = [e['path'] for e in entries]
    assert len(paths) == len(set(paths))
    expected = set(paths)
    actual = {p.relative_to(ROOT).as_posix() for sub in ['source', 'versions', 'related']
              for p in (ROOT / sub).rglob('*') if p.is_file() and p.name != 'README.md'}
    assert actual == expected, {'unlisted': sorted(actual - expected), 'missing': sorted(expected - actual)}
    image_count = 0
    dimensions = Counter()
    for entry in entries:
        path = ROOT / entry['path']
        assert not path.is_symlink()
        data = path.read_bytes()
        assert len(data) == entry['bytes'], entry['path']
        assert hashlib.sha256(data).hexdigest() == entry['sha256'], entry['path']
        assert entry['transformation'] == 'none'
        assert not set(path.relative_to(ROOT).parts) & {'.git', 'bin', 'gen', 'build', 'libs', '.idea', 'xcuserdata'}
        assert path.suffix not in {'.jar', '.class', '.apk', '.dex', '.so', '.a', '.keystore', '.p12'}
        if path.suffix in {'.bmp', '.png'}:
            image_count += 1
            result = inspect_image(path)
            dimensions[f"{result['format']}:{result['width']}x{result['height']}"] += 1
    # Scan public text, including provenance/docs, for concrete secret and local/private endpoint forms.
    forbidden = {
        'private_key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
        'token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|AIza[A-Za-z0-9_-]{30,}|AKIA[0-9A-Z]{16})\b'),
        'machine_path': re.compile(r'/(?:Users|home)/[A-Za-z0-9_.-]+|[A-Z]:\\(?:Users|Documents)'),
        'private_endpoint': re.compile(r'https?://(?:localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+)(?:[:/]|\b)'),
        'credential_assignment': re.compile(r'(?i)\b(?:password|api[_-]?key|access[_-]?token|client[_-]?secret)\b\s*[:=]\s*[\"\'][^\"\']{8,}[\"\']'),
    }
    scan_paths = [ROOT / p for p in paths if (ROOT / p).suffix not in {'.bmp', '.png'}]
    scan_paths += [p for name in ['README.md', 'SUMMARY.md', 'SKILL.md', '.gitattributes'] if (p := ROOT / name).exists()]
    scan_paths += list((ROOT / 'docs').glob('*.md')) + list((ROOT / 'related').rglob('README.md'))
    scan_paths += [ROOT / 'recovery/manifest.json', Path(__file__).resolve()]
    findings = []
    for p in scan_paths:
        text = p.read_text()
        for rule, pattern in forbidden.items():
            if pattern.search(text):
                findings.append({'path': p.relative_to(ROOT).as_posix(), 'rule': rule})
    assert not findings, findings
    variants = dict(Counter(e['variant'] for e in entries))
    android = [check_android(p) for p in ['source', 'versions/eclipse-2014', 'versions/android-studio/app/src/main']]
    result = {'status': 'passed', 'scope': 'Offline source/resource integrity and bounded static checks; no app build or execution.',
              'manifest_files_verified': len(entries), 'manifest_bytes_verified': sum(e['bytes'] for e in entries),
              'variant_file_counts': variants, 'image_files_checked': image_count,
              'image_dimensions': dict(sorted(dimensions.items())), 'android_resources': android,
              'public_text_files_scanned': len(scan_paths), 'secret_or_private_endpoint_findings': findings,
              'dependencies_bundled': False, 'app_build_attempted': False, 'app_runtime_tested': False,
              'related_ios_fragment_standalone_buildable': False}
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    try:
        main()
    except (AssertionError, OSError, ValueError, ET.ParseError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
