#!/usr/bin/env python3
"""Input-driven scientific SVG helpers. No scientific case answers or network calls."""
import argparse
import copy
import hashlib
import importlib.util
import json
import math
import pathlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
INK = 'http://www.inkscape.org/namespaces/inkscape'
ET.register_namespace('', NS)
ET.register_namespace('inkscape', INK)


def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def write(path, value):
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    temp = p.with_name(p.name + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(p)


def elem(parent, tag, **attrs):
    return ET.SubElement(parent, '{%s}%s' % (NS, tag), {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def text(parent, ident, label, x, y, size=16, anchor='middle'):
    t = elem(parent, 'text', id=ident, x=x, y=y, font_size=size, text_anchor=anchor, fill='#17212B')
    lines = str(label).split('\n')
    for i, line in enumerate(lines):
        span = elem(t, 'tspan', x=x, dy=0 if i == 0 else size * 1.25)
        span.text = line
    return t


def cmd_run(args):
    try:
        r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90)
        return {'command': args, 'returncode': r.returncode, 'stdout': r.stdout[-12000:], 'stderr': r.stderr[-6000:]}
    except (OSError, subprocess.TimeoutExpired) as e:
        return {'command': args, 'returncode': None, 'error': str(e)}


def inspect(a):
    root = pathlib.Path(a.input)
    files = []
    for p in sorted(root.rglob('*')):
        if p.is_file():
            files.append({'path': str(p), 'relative': str(p.relative_to(root)), 'bytes': p.stat().st_size, 'sha256': sha(p)})
    tools = {n: shutil.which(n) for n in ['inkscape', 'rsvg-convert', 'pdftotext', 'pdftoppm', 'pdfinfo', 'pdffonts', 'fc-match', 'tesseract', 'libreoffice', 'dot', 'gs']}
    write(a.out, {'files': files, 'tools': tools, 'python': sys.version, 'optional_modules': {m: importlib.util.find_spec(m) is not None for m in ['cairosvg', 'PIL', 'jsonschema', 'fitz', 'matplotlib']}})


def render(a):
    s = read(a.spec)
    width, height = float(s['width']), float(s['height'])
    if width <= 0 or height <= 0:
        raise ValueError('Canvas dimensions must be positive')
    nodes = s.get('nodes', [])
    ids = [n['id'] for n in nodes] + [g['id'] for g in s.get('groups', [])] + [e['id'] for e in s.get('edges', [])]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate semantic IDs')
    by_id = {n['id']: n for n in nodes}
    for n in nodes + s.get('groups', []):
        if n['w'] <= 0 or n['h'] <= 0:
            raise ValueError('Node/group size must be positive')
    root = ET.Element('{%s}svg' % NS, {'width': str(s.get('width_mm', width * 25.4 / 96)) + 'mm', 'height': str(s.get('height_mm', height * 25.4 / 96)) + 'mm', 'viewBox': '0 0 %s %s' % (width, height), 'font-family': s.get('font_family', 'DejaVu Sans, sans-serif')})
    elem(root, 'title').text = s.get('title', 'Scientific diagram')
    defs = elem(root, 'defs')
    arrow = elem(defs, 'marker', id='marker-arrow', viewBox='0 0 10 10', refX=10, refY=5, markerWidth=7, markerHeight=7, orient='auto', markerUnits='strokeWidth')
    elem(arrow, 'path', d='M0,0 L10,5 L0,10 Z', fill='#263746')
    bar = elem(defs, 'marker', id='marker-inhibition', viewBox='0 0 10 14', refX=8, refY=7, markerWidth=7, markerHeight=10, orient='auto', markerUnits='strokeWidth')
    elem(bar, 'path', d='M8,0 L8,14', fill='none', stroke='#263746', stroke_width=2)
    elem(root, 'rect', x=0, y=0, width=width, height=height, fill=s.get('background', '#FFFFFF'))
    layers = {}
    for name in ['compartments', 'edges', 'entities', 'labels', 'legend']:
        layers[name] = elem(root, 'g', id='layer-' + name)
        layers[name].set('{%s}groupmode' % INK, 'layer')
        layers[name].set('{%s}label' % INK, name)
    for g in s.get('groups', []):
        p = elem(layers['compartments'], 'g', id=g['id'])
        elem(p, 'rect', x=g['x'], y=g['y'], width=g['w'], height=g['h'], rx=10, fill=g.get('fill', '#F8FAFC'), stroke=g.get('stroke', '#7E909F'), stroke_width=1.5)
        text(p, g['id'] + '-label', g['label'], g['x'] + 12, g['y'] + 24, 16, 'start')
    for e in s.get('edges', []):
        kind = e['kind']
        if kind not in ['activation', 'inhibition', 'association', 'sequence', 'arrow']:
            raise ValueError('Unsupported edge kind: ' + kind)
        n, m = by_id[e['source']], by_id[e['target']]
        def center(q):
            return (q['x'] + q['w'] / 2, q['y'] + q['h'] / 2)
        c, d = center(n), center(m)
        dx, dy = d[0] - c[0], d[1] - c[1]
        if dx == 0 and dy == 0:
            raise ValueError('Self/overlapping-center edges require custom geometry')
        def boundary(q, cx, cy, vx, vy):
            scale = min(q['w'] / (2 * abs(vx)) if vx else math.inf, q['h'] / (2 * abs(vy)) if vy else math.inf)
            return [cx + vx * scale, cy + vy * scale]
        points = e.get('points') or [boundary(n, *c, dx, dy), boundary(m, *d, -dx, -dy)]
        if len(points) < 2:
            raise ValueError('Edge needs at least two points')
        p = elem(layers['edges'], 'g', id=e['id'])
        line = elem(p, 'polyline', points=' '.join('%s,%s' % tuple(q) for q in points), fill='none', stroke='#263746', stroke_width=2)
        if kind != 'association':
            line.set('marker-end', 'url(#marker-inhibition)' if kind == 'inhibition' else 'url(#marker-arrow)')
        if e.get('dashed'):
            line.set('stroke-dasharray', '5 4')
        if e.get('label'):
            x = (points[0][0] + points[-1][0]) / 2
            y = (points[0][1] + points[-1][1]) / 2 - 12
            text(layers['labels'], e['id'] + '-label', e['label'], e.get('label_x', x), e.get('label_y', y), s.get('font_size', 16) * .85)
    for n in nodes:
        p = elem(layers['entities'], 'g', id=n['id'])
        elem(p, 'rect', id=n['id'] + '-shape', x=n['x'], y=n['y'], width=n['w'], height=n['h'], rx=n.get('radius', 8), fill=n.get('fill', '#E3EDF4'), stroke=n.get('stroke', '#344C60'), stroke_width=1.5)
        size = s.get('font_size', 16)
        lines = len(n['label'].split('\n'))
        text(p, n['id'] + '-label', n['label'], n['x'] + n['w']/2, n['y'] + n['h']/2 + size*.35 - (lines-1)*size*.625, size)
    for i, item in enumerate(s.get('legend', [])):
        x, y = item.get('x', 30), item.get('y', height - 25 - i*26)
        elem(layers['legend'], 'rect', x=x, y=y-13, width=16, height=16, fill=item['color'], stroke='#344C60')
        text(layers['legend'], 'legend-label-%s' % i, item['label'], x+25, y, s.get('font_size', 16)*.9, 'start')
    p = pathlib.Path(a.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(str(p), encoding='utf-8', xml_declaration=True)
    audit(argparse.Namespace(svg=str(p), out=str(p.with_suffix('.svg_checks.json'))))


def patch(a):
    original = ET.parse(a.svg, parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    tree = copy.deepcopy(original)
    index = {}
    for e in tree.iter():
        if e.get('id'):
            if e.get('id') in index:
                raise ValueError('Duplicate source ID: ' + e.get('id'))
            index[e.get('id')] = e
    changes = []
    for op in read(a.changes):
        e = index[op['id']]
        before = ET.tostring(e, encoding='unicode')
        if op['op'] == 'attrs':
            for k, v in op['value'].items():
                if k == 'id' or k.startswith('on'):
                    raise ValueError('ID changes and event handlers not supported')
                e.set(k, str(v))
        elif op['op'] == 'text':
            if e.tag.rsplit('}', 1)[-1] not in ['text', 'tspan']:
                raise ValueError('Text edit target must be text/tspan')
            if len(e) == 0:
                e.text = str(op['value'])
            elif len(e) == 1 and e[0].tag.rsplit('}', 1)[-1] == 'tspan' and len(e[0]) == 0:
                e[0].text = str(op['value'])
            else:
                raise ValueError('Complex text: edit individual tspan IDs or use source-aware code')
        else:
            raise ValueError('Unknown operation: ' + op['op'])
        changes.append({'id': op['id'], 'operation': op['op'], 'before': before, 'after': ET.tostring(e, encoding='unicode')})
    if pathlib.Path(a.svg).resolve() == pathlib.Path(a.out).resolve():
        raise ValueError('Preserve original: output must differ from input')
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    tree.write(a.out, encoding='utf-8', xml_declaration=True)
    write(str(a.out) + '.changes.json', {'input': a.svg, 'input_sha256': sha(a.svg), 'output': a.out, 'output_sha256': sha(a.out), 'changes': changes, 'human_confirmation': 'not_performed'})


def audit(a):
    r = ET.parse(a.svg).getroot()
    counts, ids, texts, warnings = {}, [], [], []
    for e in r.iter():
        tag = e.tag.rsplit('}', 1)[-1]
        counts[tag] = counts.get(tag, 0)+1
        if e.get('id'):
            ids.append(e.get('id'))
        if tag == 'text':
            texts.append({'id': e.get('id'), 'text': ''.join(e.itertext())})
        if tag == 'image':
            warnings.append('Raster/image reference: inspect editability and link resolution')
    if len(ids) != len(set(ids)):
        warnings.append('Duplicate IDs')
    if not texts:
        warnings.append('No selectable SVG text; inspect whether labels were outlined/rasterized')
    if not r.get('viewBox'):
        warnings.append('Missing viewBox')
    write(a.out, {'file': a.svg, 'sha256': sha(a.svg), 'size': {'width': r.get('width'), 'height': r.get('height'), 'viewBox': r.get('viewBox')}, 'element_counts': counts, 'text': texts, 'ids': ids, 'warnings': warnings, 'scientific_review': 'not_performed_by_helper', 'visual_collision_review': 'not_performed_by_helper'})


def export(a):
    p = pathlib.Path(a.svg).resolve()
    results = []
    for fmt in ['png', 'pdf']:
        dst = p.with_suffix('.' + fmt)
        attempts = []
        successful = False
        for tool in ['inkscape', 'rsvg-convert', 'cairosvg']:
            temp = dst.with_name(dst.stem + '.exporting.' + fmt)
            if temp.exists():
                temp.unlink()
            if tool == 'inkscape' and shutil.which(tool):
                cmd = [tool, str(p), '--export-type=' + fmt, '--export-filename=' + str(temp)]
                if fmt == 'png':
                    cmd += ['--export-dpi=' + str(a.dpi)]
            elif tool == 'rsvg-convert' and shutil.which(tool):
                cmd = [tool, '-f', fmt, '-o', str(temp), '-d', str(a.dpi), '-p', str(a.dpi), str(p)]
            elif tool == 'cairosvg' and importlib.util.find_spec('cairosvg'):
                cmd = [sys.executable, '-m', 'cairosvg', str(p), '-f', fmt, '-o', str(temp)]
                if fmt == 'png':
                    # CairoSVG uses dpi for physical SVG units, preserves PDF page dimensions.
                    cmd += ['--dpi', str(a.dpi)]
            else:
                continue
            attempt = cmd_run(cmd)
            attempts.append(attempt)
            expected = b'\x89PNG\r\n\x1a\n' if fmt == 'png' else b'%PDF-'
            if attempt.get('returncode') == 0 and temp.exists() and temp.read_bytes().startswith(expected):
                temp.replace(dst)
                successful = True
                break
        item = {'format': fmt, 'path': str(dst), 'status': 'exported' if successful else 'failed', 'attempts': attempts}
        if successful and fmt == 'png' and importlib.util.find_spec('PIL'):
            from PIL import Image
            with Image.open(dst) as im:
                im.load()
                dpi_temp = dst.with_name(dst.stem + '.dpi.png')
                im.save(dpi_temp, dpi=(a.dpi, a.dpi))
            dpi_temp.replace(dst)
            item['dpi_metadata_action'] = 'written at requested export DPI using Pillow'
        if successful:
            item.update({'sha256': sha(dst), 'bytes': dst.stat().st_size})
            if fmt == 'png' and importlib.util.find_spec('PIL'):
                from PIL import Image
                with Image.open(dst) as im:
                    im.load()
                    item['measured'] = {'pixels': list(im.size), 'mode': im.mode, 'dpi': im.info.get('dpi'), 'format': im.format}
                if not item['measured']['dpi']:
                    item['dpi_metadata'] = 'absent; pixel dimensions must be checked against physical size'
            if fmt == 'pdf':
                for tool in ['pdfinfo', 'pdffonts']:
                    if shutil.which(tool):
                        item[tool] = cmd_run([tool, str(dst)])
        results.append(item)
    write(a.out, {'source': str(p), 'source_sha256': sha(p), 'requested_dpi': a.dpi, 'exports': results, 'status': 'success' if all(x['status'] == 'exported' for x in results) else 'partial', 'scientific_validation': 'not_performed_by_exporter'})


def contract_shape(contract):
    if isinstance(contract, dict):
        if isinstance(contract.get('properties'), dict):
            return contract.get('required', list(contract['properties'])), contract['properties'], contract
        if isinstance(contract.get('required'), list) and 'properties' not in contract:
            return contract['required'], {}, None
        if 'fields' in contract and isinstance(contract['fields'], (dict, list)):
            return contract_shape(contract['fields'])
        return list(contract), contract, None
    if isinstance(contract, list):
        names, types = [], {}
        for item in contract:
            if isinstance(item, str):
                names.append(item)
            elif isinstance(item, dict):
                name = item.get('name', item.get('field', item.get('key')))
                if name:
                    names.append(name)
                    types[name] = item
        return names, types, None
    return [], {}, None


def finalize(a):
    case, report = read(a.case), read(a.report)
    if not isinstance(report, dict) or 'case_id' not in case:
        raise ValueError('Report must be an object; original case_id must exist')
    if 'case_id' in report and report['case_id'] != case['case_id']:
        raise ValueError('Report case_id conflicts with original')
    report['case_id'] = case['case_id']
    keys, types, schema = contract_shape(case.get('output_contract'))
    errors = ['Missing original contract field: ' + k for k in keys if k not in report]
    python_types = {'string': str, 'object': dict, 'array': list, 'boolean': bool, 'number': (int, float), 'integer': int, 'null': type(None)}
    for k, descriptor in types.items():
        if k not in report or not isinstance(descriptor, dict):
            continue
        typ = descriptor.get('type')
        allowed = typ if isinstance(typ, list) else [typ]
        known = [t for t in allowed if isinstance(t, str) and t in python_types]
        if known and not any(isinstance(report[k], python_types[t]) and (t not in ['integer', 'number'] or not isinstance(report[k], bool)) for t in known):
            errors.append('Wrong field type for ' + k + ': ' + str(typ))
    if schema and importlib.util.find_spec('jsonschema'):
        import jsonschema
        try:
            jsonschema.validate(report, schema)
        except (jsonschema.ValidationError, jsonschema.SchemaError) as e:
            errors.append('JSON Schema: ' + str(e))
    if errors:
        raise ValueError('\n'.join(errors))
    write(a.out, report)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    commands = {'inspect': [('input', '/input'), ('out', None)], 'render': [('spec', None), ('out', None)], 'patch': [('svg', None), ('changes', None), ('out', None)], 'audit': [('svg', None), ('out', None)], 'export': [('svg', None), ('out', None)], 'finalize': [('case', None), ('report', None), ('out', None)]}
    for name, opts in commands.items():
        p = subs.add_parser(name)
        for key, default in opts:
            p.add_argument('--' + key, default=default, required=default is None)
        if name == 'export':
            p.add_argument('--dpi', type=float, default=300)
        p.set_defaults(func=globals()[name])
    a = parser.parse_args()
    try:
        a.func(a)
    except Exception as e:
        print(json.dumps({'status': 'failed', 'command': a.command, 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({'status': 'completed', 'command': a.command, 'output': a.out}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
