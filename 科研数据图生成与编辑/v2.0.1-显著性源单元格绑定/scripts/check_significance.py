#!/usr/bin/env python3
"""Verify significance text at its stable SVG ID against the exact reloaded source cell."""
import argparse
import json
import pathlib
import sys
import xml.etree.ElementTree as ET
from charts import load, table, digest


def visible_text(root, ident):
    for elem in root.iter():
        if elem.get('id') == ident:
            return ' '.join(''.join(elem.itertext()).split())
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', required=True)
    parser.add_argument('--svg', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    checks, cache = [], {}
    try:
        report = load(args.map)
        root = ET.parse(args.svg).getroot()
        annotations = [item for item in report['elements'] if item.get('annotation', {}).get('text_column')]
        if not annotations:
            raise ValueError('No source-bound significance annotations in source map')
        for item in annotations:
            ident = item['element_id']
            if len(item.get('source_cells', [])) != 1:
                raise ValueError('Significance annotation must have exactly one source cell: ' + ident)
            c = item['source_cells'][0]
            key = (c['file'], c.get('sheet') or 0)
            if key not in cache:
                headers, rows, _ = table(c['file'], c.get('sheet') or 0)
                cache[key] = (digest(c['file']), headers, rows)
            sha, headers, rows = cache[key]
            index = c['row'] - 2
            exists = 0 <= index < len(rows) and c['column'] in headers
            raw = rows[index][c['column']] if exists else None
            expected = str(raw).strip() if raw is not None else ''
            actual = visible_text(root, ident)
            passed = bool(sha == c['sha256'] and exists and raw == c['raw_value'] and expected and actual == expected)
            checks.append({'element_id': ident, 'check': 'significance_cell_and_svg_text', 'passed': passed,
                           'locator': '%s:%s:%s:%s' % (c['file'], c.get('sheet'), c['row'], c['column']),
                           'expected': expected, 'actual': actual})
        result = {'status': 'passed' if all(c['passed'] for c in checks) else 'failed', 'checks': checks}
    except Exception as exc:
        result = {'status': 'failed', 'error': str(exc), 'checks': checks}
    pathlib.Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    sys.exit(main())
