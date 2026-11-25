#!/usr/bin/env python3
"""Verify grouped bars follow the reference category registry without losing logical row IDs."""
import argparse
import json
import pathlib
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--map', required=True)
    args = parser.parse_args()
    checks = []
    try:
        report = json.loads(pathlib.Path(args.map).read_text(encoding='utf-8'))
        alignments = report.get('category_alignments', [])
        if not alignments:
            raise ValueError('No reordered grouped-bar series in this source map')
        for item in alignments:
            bars = [e for e in report['elements'] if e.get('panel') == item['panel'] and e.get('series') == item['series'] and 'height' in e.get('geometry', {})]
            actual_x = [str(e['values']['x']) for e in bars]
            actual_rows = [e['source_cells'][0]['row'] for e in bars]
            passed = actual_x == item['reference_order'] and actual_rows == item['aligned_logical_rows'] and actual_x != item['source_order']
            checks.append({'panel': item['panel'], 'series': item['series'], 'passed': passed,
                           'actual_category_order': actual_x, 'expected_category_order': item['reference_order'],
                           'actual_logical_rows': actual_rows, 'expected_logical_rows': item['aligned_logical_rows']})
        result = {'status': 'passed' if all(c['passed'] for c in checks) else 'failed', 'checks': checks}
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] == 'passed' else 1
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
