#!/usr/bin/env python3
"""Require a significance annotation to show the text stored in its source cell."""
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


def expected(spec, spec_path):
    texts = []
    for panel in spec['panels']:
        for anno in panel.get('annotations', []):
            column = anno.get('text_column')
            if not column:
                continue
            source = spec['sources'][anno['source']]
            path = pathlib.Path(source['path'])
            if not path.is_absolute():
                path = spec_path.parent / path
            rows = load_table(path)
            logical = anno['row']
            row = rows[logical - 2]
            token = str(row.get(column, '')).strip()
            if not token:
                raise ValueError('Blank significance text')
            texts.append(token)
    if not texts:
        raise ValueError('Spec does not set text_column')
    return texts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--svg', required=True)
    args = parser.parse_args()
    spec_path = pathlib.Path(args.spec)
    try:
        texts = expected(json.loads(spec_path.read_text(encoding='utf-8')), spec_path)
        root = ET.parse(args.svg).getroot()
        visible = '\n'.join(''.join(node.itertext()) for node in root.iter() if local(node.tag) == 'text')
        missing = [token for token in texts if token not in visible]
        ok = not missing
        print(json.dumps({'status': 'passed' if ok else 'failed', 'expected': texts, 'missing': missing}, ensure_ascii=False))
        return 0 if ok else 1
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
