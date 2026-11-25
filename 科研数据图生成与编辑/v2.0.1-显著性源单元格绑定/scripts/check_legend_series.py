#!/usr/bin/env python3
"""Compare SVG legend text and swatch with label_column and color_column. Synthetic checks only."""
import argparse
import csv
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET


def local(tag):
    return tag.split('}')[-1]


def normalize_color(value):
    text = str(value).strip().lower().replace(' ', '')
    match = re.fullmatch(r'#([0-9a-f]{3}|[0-9a-f]{6})', text)
    if not match:
        return text
    hex_digits = match.group(1)
    if len(hex_digits) == 3:
        hex_digits = ''.join(ch * 2 for ch in hex_digits)
    return '#' + hex_digits


def style_fill(style):
    match = re.search(r'(?:^|;)\s*fill\s*:\s*([^;]+)', style or '', re.I)
    if not match or match.group(1).strip().lower() == 'none':
        return None
    return normalize_color(match.group(1))


def legend_pairs(svg_path):
    root = ET.parse(svg_path).getroot()
    legends = [e for e in root.iter() if local(e.tag) == 'g' and (e.get('id') or '').startswith('legend_')]
    legends.sort(key=lambda e: e.get('id'))
    panels = []
    for legend in legends:
        fill = None
        pairs = []
        for child in list(legend):
            if local(child.tag) != 'g':
                continue
            paths = [e for e in child.iter() if local(e.tag) == 'path']
            texts = [''.join(e.itertext()).strip() for e in child.iter() if local(e.tag) == 'text']
            texts = [t for t in texts if t]
            if paths and not texts:
                fill = style_fill(paths[-1].get('style'))
            elif texts:
                if fill is None:
                    raise ValueError('Legend text has no swatch: ' + texts[0])
                pairs.append((texts[0], fill))
                fill = None
        panels.append(pairs)
    return panels


def load_table(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle, delimiter='\t' if path.suffix.lower() == '.tsv' else ',')
        headers = reader.fieldnames or []
        rows = list(reader)
    if not headers or len(headers) != len(set(headers)) or '' in headers:
        raise ValueError('Missing/duplicate column headers')
    return headers, rows


def selected_rows(headers, rows, desc):
    where = desc.get('where', {})
    if not set(where).issubset(headers):
        raise ValueError('Unknown filter column')
    ids = desc.get('rows')
    chosen = []
    for index, row in enumerate(rows):
        logical = index + 2
        if ids is not None and logical not in ids:
            continue
        if all(str(row[key]) == str(value) for key, value in where.items()):
            chosen.append(row)
    return chosen


def expected_panels(spec, spec_path):
    panels = []
    for panel in spec['panels']:
        if panel['kind'] not in ('bar', 'line', 'scatter') or panel.get('legend', True) is False:
            continue
        pairs = []
        for desc in panel['series']:
            label_col = desc.get('label_column')
            color_col = desc.get('color_column')
            if not label_col or not color_col:
                raise ValueError('Series is missing label_column or color_column')
            source = spec['sources'][desc['source']]
            path = pathlib.Path(source['path'])
            if not path.is_absolute():
                path = spec_path.parent / path
            headers, rows = load_table(path)
            found = []
            for row in selected_rows(headers, rows, desc):
                label = str(row.get(label_col, '')).strip()
                color = str(row.get(color_col, '')).strip()
                if not label or not color:
                    raise ValueError('Blank series label or color')
                found.append((label, normalize_color(color)))
            if len(set(found)) != 1:
                raise ValueError('Selected rows disagree on series label or color')
            pairs.append(found[0])
        panels.append(pairs)
    return panels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True)
    parser.add_argument('--svg', required=True)
    args = parser.parse_args()
    spec_path = pathlib.Path(args.spec)
    try:
        spec = json.loads(spec_path.read_text(encoding='utf-8'))
        expected = expected_panels(spec, spec_path)
        actual = legend_pairs(args.svg)
        ok = actual == expected
        print(json.dumps({'status': 'passed' if ok else 'failed', 'expected': expected, 'actual': actual}, ensure_ascii=False))
        return 0 if ok else 1
    except Exception as exc:
        print(json.dumps({'status': 'failed', 'error': str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
