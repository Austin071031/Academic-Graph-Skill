#!/usr/bin/env python3
"""Independently reload chart source cells and verify direct mappings, not scientific interpretation."""
import argparse
import math
import pathlib
import sys
from charts import load, save, table, digest


def verify(path):
    report = load(path)
    checks, reverse, cache = [], {}, {}
    for item in report['elements']:
        ident = item['element_id']
        cells = item.get('source_cells', [])
        for c in cells:
            key = (c['file'], c.get('sheet'))
            if key not in cache:
                headers, rows, _ = table(c['file'], c.get('sheet') or 0)
                cache[key] = (digest(c['file']), headers, rows)
            sha, headers, rows = cache[key]
            ok = sha == c['sha256']
            locator = '%s:%s:%s:%s' % (c['file'], c.get('sheet'), c['row'], c['column'])
            reverse.setdefault(locator, []).append(ident)
            rn = c['row'] - 2
            exists = 0 <= rn < len(rows) and c['column'] in headers
            checks.append({'element_id': ident, 'check': 'source_cell', 'passed': bool(ok and exists and rows[rn][c['column']] == c['raw_value']), 'locator': locator})
        values, geometry = item.get('values', {}), item.get('geometry', {})
        if 'y' in values and cells and ('height' in geometry or 'point_index' in geometry):
            checks.append({'element_id': ident, 'check': 'value_to_source', 'passed': math.isclose(float(cells[0]['raw_value']), values['y'], rel_tol=1e-12, abs_tol=1e-12)})
        if 'observations' in values:
            checks.append({'element_id': ident, 'check': 'raw_box_observations', 'passed': [float(c['raw_value']) for c in cells] == values['observations'] and values['n']==len(cells)})
        if 'value' in values and cells:
            source_value = cells[-1]['raw_value'] if 'row' in geometry else cells[0]['raw_value']
            checks.append({'element_id': ident, 'check': 'encoded_value_to_source', 'passed': math.isclose(float(source_value), values['value'], rel_tol=1e-12, abs_tol=1e-12)})
        if 'height' in geometry:
            checks.append({'element_id': ident, 'check': 'bar_mapping', 'passed': math.isclose(geometry['height'], values['y'], rel_tol=1e-12, abs_tol=1e-12) and geometry['baseline']==0})
        if 'point_index' in geometry:
            checks.append({'element_id': ident, 'check': 'point_y', 'passed': math.isclose(geometry['y'], values['y'], rel_tol=1e-12, abs_tol=1e-12)})
        if 'degrees' in geometry:
            checks.append({'element_id': ident, 'check': 'sector_fraction', 'passed': abs(geometry['degrees']-values['value']/values['total']*360)<1e-3})
    return {'status': 'passed' if checks and all(c['passed'] for c in checks) else 'failed', 'checks': checks, 'reverse_cell_index': reverse,
            'scope': 'Reloaded raw cells/hashes and direct recorded geometry; actual SVG artist geometry checked at render. Custom transforms and scientific interpretation require additional review.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map', required=True); p.add_argument('--out', required=True)
    a = p.parse_args()
    try:
        report = verify(a.map)
        save(a.out, report)
        print(report['status'])
        return 0 if report['status']=='passed' else 1
    except Exception as e:
        save(a.out, {'status': 'failed', 'error': str(e)})
        print(str(e), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
