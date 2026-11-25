#!/usr/bin/env python3
"""Require the SVG legend to contain the error-kind token from the source table."""
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
        if ids is not None and index + 2 not in ids:
            continue
        if all(str(row.get(key)) == str(value) for key, value in where.items()):
            chosen.append(row)
    return chosen


def expected(spec, spec_path):
    tokens = []
    for panel in spec['panels']:
        for desc in panel.get('series', []):
            column = desc.get('error_kind_column')
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
                    raise ValueError('Blank error kind')
                found.append(token)
            if len(set(found)) != 1:
                raise ValueError('Selected rows disagree on error kind')
            tokens.append(found[0])
    if not tokens:
        raise ValueError('Spec does not set error_kind_column')
    return tokens


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--svg', required=True)
    args = parser.parse_args()
    spec_path = pathlib.Path(args.spec)
    try:
        tokens = expected(json.loads(spec_path.read_text(encoding='utf-8')), spec_path)
        root = ET.parse(args.svg).getroot()
        text = '\n'.join(''.join(node.itertext()) for node in root.iter() if local(node.tag) == 'text')
        missing = [token for token in tokens if token not in text]
        ok = not missing
        print(json.dumps({'status': 'passed' if ok else 'failed', 'expected': tokens, 'missing': missing}, ensure_ascii=False))
        return 0 if ok else 1
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
