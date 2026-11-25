#!/usr/bin/env python3
"""Require each bar category's n=<value> text to come from the source table."""
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
        return list(reader)


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


def expected_labels(spec, spec_path):
    labels = []
    for panel in spec['panels']:
        column = panel.get('n_column')
        if not column or panel.get('kind') != 'bar':
            continue
        by_category = {}
        for desc in panel.get('series', []):
            xcol = desc.get('x')
            if not xcol:
                raise ValueError('Sample size requires a category column')
            source = spec['sources'][desc['source']]
            path = pathlib.Path(source['path'])
            if not path.is_absolute():
                path = spec_path.parent / path
            for row in selected(load_table(path), desc):
                token = str(row.get(column, '')).strip()
                category = str(row.get(xcol, '')).strip()
                if not token or not category:
                    raise ValueError('Blank sample size or category')
                by_category.setdefault(category, set()).add(token)
        if not by_category:
            raise ValueError('Sample size column selected no rows')
        for category, tokens in by_category.items():
            if len(tokens) != 1:
                raise ValueError('Category sample size disagrees: ' + category)
            labels.append('n=' + next(iter(tokens)))
    if not labels:
        raise ValueError('Spec does not set n_column on a bar panel')
    return labels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--svg', required=True)
    args = parser.parse_args()
    spec_path = pathlib.Path(args.spec)
    try:
        spec = json.loads(spec_path.read_text(encoding='utf-8'))
        labels = expected_labels(spec, spec_path)
        text = svg_text(args.svg)
        missing = [label for label in labels if label not in text]
        ok = not missing
        print(json.dumps({'status': 'passed' if ok else 'failed', 'expected': labels, 'missing': missing}, ensure_ascii=False))
        return 0 if ok else 1
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
