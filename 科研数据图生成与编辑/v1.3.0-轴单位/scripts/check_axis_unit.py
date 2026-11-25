#!/usr/bin/env python3
"""Require the y-axis label to contain the unit column from the source table."""
import argparse
import csv
import json
import pathlib
import sys
import xml.etree.ElementTree as ET


def local(tag):
    return tag.split('}')[-1]


def load_table(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t' if path.suffix.lower() == '.tsv' else ',')
        rows = list(reader)
    return rows


def selected(rows, desc):
    where = desc.get('where', {})
    ids = desc.get('rows')
    chosen = []
    for index, row in enumerate(rows):
        logical = index + 2
        if ids is not None and logical not in ids:
            continue
        if all(str(row.get(key)) == str(value) for key, value in where.items()):
            chosen.append(row)
    return chosen


def svg_text(path):
    root = ET.parse(path).getroot()
    return '\n'.join(''.join(node.itertext()) for node in root.iter() if local(node.tag) == 'text')


def expected_units(spec, spec_path):
    units = []
    for panel in spec['panels']:
        panel_units = []
        for desc in panel.get('series', []):
            column = desc.get('unit_column') or panel.get('unit_column')
            if not column:
                continue
            source = spec['sources'][desc['source']]
            path = pathlib.Path(source['path'])
            if not path.is_absolute():
                path = spec_path.parent / path
            found = []
            for row in selected(load_table(path), desc):
                token = str(row.get(column, '')).strip()
                if not token:
                    raise ValueError('Blank unit')
                found.append(token)
            if len(set(found)) != 1:
                raise ValueError('Selected rows disagree on unit')
            panel_units.append(found[0])
        if not panel_units:
            continue
        if len(set(panel_units)) != 1:
            raise ValueError('Panel series disagree on unit')
        units.append(panel_units[0])
    if not units:
        raise ValueError('Spec does not set unit_column')
    return units


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--svg', required=True)
    args = parser.parse_args()
    spec_path = pathlib.Path(args.spec)
    try:
        spec = json.loads(spec_path.read_text(encoding='utf-8'))
        units = expected_units(spec, spec_path)
        text = svg_text(args.svg)
        missing = [unit for unit in units if unit not in text]
        ok = not missing
        print(json.dumps({'status': 'passed' if ok else 'failed', 'expected': units, 'missing': missing}, ensure_ascii=False))
        return 0 if ok else 1
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
