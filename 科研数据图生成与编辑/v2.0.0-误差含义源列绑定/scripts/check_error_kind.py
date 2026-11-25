#!/usr/bin/env python3
"""Verify exact error-kind annotations and independently reload their source cells."""
import argparse
import json
import pathlib
import sys
import xml.etree.ElementTree as ET
from charts import load, table, digest


def native_text(root, ident):
    for elem in root.iter():
        if elem.get('id') == ident:
            return ' '.join(''.join(elem.itertext()).split())
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--svg', required=True)
    parser.add_argument('--map', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    checks = []
    try:
        spec_path = pathlib.Path(args.spec).resolve()
        spec = load(spec_path)
        report = load(args.map)
        root = ET.parse(args.svg).getroot()
        by_id = {item['element_id']: item for item in report['elements']}
        expected = 0
        cache = {}
        for pi, panel in enumerate(spec['panels']):
            for si, desc in enumerate(panel.get('series', [])):
                column = desc.get('error_kind_column')
                if not column:
                    continue
                expected += 1
                source = spec['sources'][desc['source']]
                path = pathlib.Path(source['path'])
                path = path if path.is_absolute() else spec_path.parent / path
                path = path.resolve()
                key = (str(path), source.get('sheet', 0))
                if key not in cache:
                    headers, rows, _ = table(path, source.get('sheet', 0))
                    cache[key] = (digest(path), headers, rows)
                sha, headers, rows = cache[key]
                ids = desc.get('rows')
                where = desc.get('where', {})
                selected = [(i+2, r) for i, r in enumerate(rows)
                            if (ids is None or i+2 in ids) and all(str(r[k]) == str(v) for k, v in where.items())]
                tokens = [str(r[column]).strip() for _, r in selected]
                ident = 'panel-%d-series-%d-error-kind' % (pi, si)
                actual = native_text(root, ident)
                ok = bool(tokens and len(set(tokens)) == 1 and actual == 'Error: ' + tokens[0])
                checks.append({'element_id': ident, 'check': 'error_kind_svg_text', 'passed': ok,
                               'expected': tokens, 'actual': actual, 'source_sha256': sha})
                item = by_id.get(ident)
                expected_cells = [{'row': rn, 'column': column, 'raw_value': r[column]} for rn, r in selected]
                actual_cells = [] if item is None else [{k: c.get(k) for k in ('row', 'column', 'raw_value')} for c in item['source_cells']]
                checks.append({'element_id': ident, 'check': 'error_kind_source_cells',
                               'passed': actual_cells == expected_cells, 'expected': expected_cells, 'actual': actual_cells})
        if not expected:
            raise ValueError('No error_kind_column annotations in spec')
        result = {'status': 'passed' if all(c['passed'] for c in checks) else 'failed', 'checks': checks}
    except Exception as exc:
        result = {'status': 'failed', 'error': str(exc), 'checks': checks}
    pathlib.Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
