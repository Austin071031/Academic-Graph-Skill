#!/usr/bin/env python3
"""Compose runtime-authored panels into an editable, source-linked graphical abstract."""
import argparse
import copy
import json
import math
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
import diagram as D
import pathway as P

ROLES = {'question', 'methods', 'results', 'conclusion'}


def finite(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def local(base, value):
    p = pathlib.Path(value)
    return p.resolve() if p.is_absolute() else (base / p).resolve()


def wrap(value, width, size):
    """Conservative text advance estimate; real rendered review remains required."""
    result = []
    for paragraph in str(value).split('\n'):
        line, advance = '', 0
        for token in re.findall(r'[^\W_]+|\s+|[^\w\s]', paragraph, re.UNICODE):
            # Break CJK strings characterwise, Latin words as units when possible.
            chunks = list(token) if any(ord(c) > 0x2FFF for c in token) else [token]
            for chunk in chunks:
                length = sum(1 if ord(c) > 0x2FFF else .62 for c in chunk) * size
                if advance + length > width and line.strip():
                    result.append(line.rstrip())
                    line, advance = '', 0
                if not line:
                    chunk = chunk.lstrip()
                    length = sum(1 if ord(c) > 0x2FFF else .62 for c in chunk) * size
                line += chunk
                advance += length
        result.append(line.rstrip())
    return result


def add_text(parent, ident, value, x, y, width, size, weight='normal', fill='#233747'):
    lines = wrap(value, width, size)
    t = D.text(parent, ident, '\n'.join(lines), x, y, size, 'start')
    t.set('font-weight', weight)
    t.set('fill', fill)
    return len(lines) * size * 1.25


def validate(s):
    errors, warnings = [], []
    for key in ['width', 'height', 'width_mm', 'height_mm']:
        if not finite(s.get(key)) or s[key] <= 0:
            errors.append('Positive finite dimension required: ' + key)
    if errors:
        return errors, warnings
    if abs(s['width']/s['height'] - s['width_mm']/s['height_mm']) > .001:
        errors.append('Physical/viewBox aspect ratios disagree')
    if not s.get('title'):
        errors.append('Missing source-supported title')
    if not finite(s.get('font_size',20)) or s.get('font_size',20) <= 0:
        errors.append('Positive finite font_size required')
    if not isinstance(s.get('panels'),list) or not s['panels']:
        return errors+['At least one authored panel is required'],warnings
    roles, ids = set(), set()
    for panel in s.get('panels', []):
        ident = panel.get('id', '')
        if not re.fullmatch(r'[A-Za-z_][\w.-]*', ident) or ident in ids or ident.startswith('ga-'):
            errors.append('Invalid, reserved or duplicate panel ID: ' + ident)
        ids.add(ident)
        pr = panel.get('roles', [])
        if not isinstance(pr, list) or not set(pr).issubset(ROLES):
            errors.append('Panel roles must be a list drawn from ' + ','.join(sorted(ROLES)))
        else:
            roles.update(pr)
        if not panel.get('title') or not panel.get('evidence'):
            errors.append('Panel needs title and actual evidence references: ' + ident)
        good = all(finite(panel.get(k)) for k in ['x', 'y', 'w', 'h'])
        if not good or panel.get('w', 0) <= 0 or panel.get('h', 0) <= 0:
            errors.append('Invalid panel geometry: ' + ident)
        elif not P.contains((0, 0, s['width'], s['height']), P.bounds(panel)):
            errors.append('Panel outside canvas: ' + ident)
        if not panel.get('asset') and not panel.get('body'):
            errors.append('Panel has neither editable visual asset nor source-supported body: ' + ident)
        if not panel.get('asset') and any(r in pr for r in ['methods', 'results']):
            warnings.append('Methods/results panel lacks a visual; create a source-grounded diagram/chart: ' + ident)
    for role in sorted(ROLES - roles):
        warnings.append('Unrepresented narrative role: ' + role)
    panels = s.get('panels', [])
    for i, p in enumerate(panels):
        for q in panels[i+1:]:
            if all(finite(v.get(k)) for v in [p, q] for k in ['x', 'y', 'w', 'h']):
                if P.overlap(P.bounds(p), P.bounds(q)):
                    warnings.append('Panel overlap: ' + p['id'] + '/' + q['id'])
    return errors, warnings


def import_svg(path, parent, prefix, x, y, w, h):
    source = ET.parse(path).getroot()
    box = source.get('viewBox')
    if not box:
        raise ValueError('Asset requires explicit viewBox: ' + str(path))
    vb = [float(t) for t in re.split(r'[ ,]+', box.strip())]
    if len(vb) != 4 or not all(finite(t) for t in vb) or min(vb[2:]) <= 0:
        raise ValueError('Invalid asset viewBox')
    ids = [e.get('id') for e in source.iter() if e.get('id')]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate asset IDs')
    for parent_node in source.iter():
        for child in list(parent_node):
            if child.tag.rsplit('}', 1)[-1] == 'style':
                css = ''.join(child.itertext()).strip()
                match = re.fullmatch(r'\*\s*\{([^{}]+)\}', css)
                if not match or not all(v.strip().split(':')[0].strip() in ['stroke-linejoin','stroke-linecap'] for v in match[1].split(';') if v.strip()):
                    raise ValueError('Complex asset CSS must be resolved to native inline attributes first')
                source.set('style', match[1]+';'+source.get('style',''))
                parent_node.remove(child)
    if any(e.tag.rsplit('}', 1)[-1] in ['script', 'foreignObject', 'image'] for e in source.iter()):
        raise ValueError('Asset includes script, foreignObject or raster. Resolve to native styled SVG first')
    # ID prefixes prevent defs/clip/marker collisions. Exact fragment references are rewritten.
    replacements = {ident: prefix + ident for ident in ids}
    group = ET.SubElement(parent, '{%s}svg' % D.NS, {
        'id': prefix + 'viewport', 'x': str(x), 'y': str(y), 'width': str(w), 'height': str(h),
        'viewBox': box, 'preserveAspectRatio': 'xMidYMid meet', 'overflow': 'hidden'})
    for k in ['font-family', 'font-size', 'font-weight', 'font-style', 'font-variant',
              'font-stretch', 'text-anchor', 'dominant-baseline', 'letter-spacing',
              'word-spacing', 'direction', 'writing-mode', 'color', 'fill',
              'fill-opacity', 'fill-rule', 'stroke', 'stroke-width', 'stroke-opacity',
              'stroke-linejoin', 'stroke-linecap', 'stroke-dasharray', 'stroke-dashoffset',
              'opacity', 'visibility', 'style']:
        if source.get(k) is not None:
            group.set(k, source.get(k))
    scale = min(w/vb[2], h/vb[3])
    offset_x, offset_y = x+(w-vb[2]*scale)/2, y+(h-vb[3]*scale)/2
    font_sizes = []
    def collect_fonts(node, inherited=None):
        style = dict(re.findall(r'([\w-]+)\s*:\s*([^;]+)',node.get('style','')))
        raw = style.get('font-size',node.get('font-size',inherited))
        if raw is not None and node.tag.rsplit('}',1)[-1] in ['text','tspan'] and (node.text or '').strip():
            match = re.fullmatch(r'([\d.]+)(px|pt)?',str(raw).strip())
            if match:
                font_sizes.append(float(match[1])*(4/3 if match[2]=='pt' else 1))
        for child in node:
            collect_fonts(child,raw)
    collect_fonts(source)
    for original in source:
        e = copy.deepcopy(original)
        for node in e.iter():
            for key, val in list(node.attrib.items()):
                if key == 'id':
                    node.set(key, replacements[val])
                elif key.rsplit('}', 1)[-1] == 'href':
                    if not val.startswith('#') or val[1:] not in replacements:
                        raise ValueError('Unresolved linked asset: ' + val)
                    node.set(key, '#' + replacements[val[1:]])
                else:
                    node.set(key, re.sub(r'url\(\s*[\"\']?#([^\s)\"\']+)[\"\']?\s*\)',
                        lambda m: 'url(#' + replacements[m[1]] + ')', val))
        group.append(e)
    return {'source': str(path), 'sha256': D.sha(path), 'id_map': replacements,
            'placement': {'x': offset_x, 'y': offset_y, 'scale': scale, 'viewBox': vb},
            'minimum_text_user_units':min(font_sizes) if font_sizes else None}


def render(a):
    spec_path = pathlib.Path(a.spec).resolve()
    s = D.read(spec_path)
    errors, warnings = validate(s)
    if errors:
        raise ValueError('\n'.join(errors))
    w, h = s['width'], s['height']
    root = ET.Element('{%s}svg' % D.NS, {'width': str(s['width_mm'])+'mm',
        'height': str(s['height_mm'])+'mm', 'viewBox': '0 0 %s %s' % (w,h),
        'font-family': s.get('font_family', 'DejaVu Sans, sans-serif')})
    D.elem(root, 'title').text = s['title']
    D.elem(root, 'desc').text = 'Editable source-bound graphical abstract. Evidence and checks are sidecars.'
    D.elem(root, 'rect', id='ga-background', width=w, height=h, fill=s.get('background', '#FFFFFF'))
    layers = {}
    for name in ['narrative', 'panels', 'legend']:
        layer = D.elem(root, 'g', id='ga-'+name)
        layer.set('{%s}groupmode' % D.INK, 'layer')
        layer.set('{%s}label' % D.INK, name)
        layers[name] = layer
    font = s.get('font_size', 20)
    heading_h = add_text(layers['narrative'], 'ga-title', s['title'], 28, 38, w-56, font*1.3, 'bold')
    if 26+heading_h > min(p['y'] for p in s['panels']):
        warnings.append('Title may overlap first panel')
    imports, source_map = [], []
    for index, panel in enumerate(s['panels']):
        x,y,pw,ph = [panel[k] for k in ['x','y','w','h']]
        ident = panel['id']
        p = D.elem(layers['panels'], 'g', id=ident)
        p.set('data-roles', ' '.join(panel.get('roles', [])))
        D.elem(p, 'rect', id=ident+'--rule', x=x,y=y,width=pw,height=3,fill=panel.get('accent','#0072B2'))
        title_h = add_text(p, ident+'--title', panel['title'], x+8,y+font*1.5,pw-16,font,'bold')
        cy = y + font*.5 + title_h + 14
        if panel.get('body'):
            bh = add_text(p, ident+'--body', panel['body'], x+8,cy+font*.75,pw-16,font*.9)
            cy += bh+16
        footer = panel.get('takeaway')
        footer_h = len(wrap(footer, pw-16,font*.9))*font*1.125+18 if footer else 0
        available = y+ph-cy-footer_h-8
        asset_info = None
        if panel.get('asset'):
            if available < 30:
                raise ValueError('No room for asset: '+ident)
            path = local(spec_path.parent, panel['asset'])
            asset_info = import_svg(path,p,ident+'--asset-',x+8,cy,pw-16,available)
            minimum = asset_info['minimum_text_user_units']
            if minimum is not None:
                pt = minimum*asset_info['placement']['scale']*s['width_mm']/w*72/25.4
                asset_info['approximate_minimum_text_pt'] = pt
                if pt < 7:
                    warnings.append('Scaled asset labels below 7 pt (approximate; inspect transforms): '+ident+' '+str(round(pt,2)))
            imports.append({'panel':ident,**asset_info})
        elif cy > y+ph-footer_h:
            warnings.append('Panel text may exceed panel: '+ident)
        if footer:
            add_text(p,ident+'--takeaway',footer,x+8,y+ph-footer_h+font,pw-16,font*.9,'bold')
        source_map.append({'element_id':ident,'roles':panel.get('roles',[]),
            'evidence':panel['evidence'],'elements':panel.get('elements',[]), 'asset':asset_info})
    legend_y = s.get('legend_y', h-26)
    if s.get('legend'):
        add_text(layers['legend'],'ga-legend-text',s['legend'],28,legend_y,w-56,font*.75)
        if max(p['y']+p['h'] for p in s['panels']) > legend_y-font:
            warnings.append('Legend may overlap panels')
    dest = pathlib.Path(a.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(dest,encoding='utf-8',xml_declaration=True)
    D.write(str(dest)+'.composition.json',{'spec_sha256':D.sha(spec_path),'output_sha256':D.sha(dest),
        'panels':source_map,'imports':imports,'warnings':warnings,'version':'1.0.0',
        'scientific_review':'requires_agent_review','visual_review':'not_performed_by_compositor'})


def check(a):
    spec_path = pathlib.Path(a.spec).resolve()
    s = D.read(spec_path)
    errors,warnings = validate(s)
    evidence = s.get('evidence',{})
    refs = []
    for ident,ref in evidence.items():
        try:
            if D.sha(ref['path']) != ref['sha256']:
                raise ValueError('hash mismatch')
            if not ref.get('locator'):
                raise ValueError('source locator required')
            text = P.source_text(ref)
            if ref.get('quote') and text is not None:
                norm = lambda v: re.sub(r'\s+',' ',v).strip()
                if norm(ref['quote']) not in norm(text):
                    raise ValueError('quote not found')
            else:
                warnings.append('Visual/data evidence needs Agent review: '+ident)
            refs.append({'id':ident,'source_hash':'matches','semantic_review':'requires_agent_review'})
        except (OSError,ValueError,KeyError,IndexError) as ex:
            errors.append('Evidence '+ident+': '+str(ex))
    for panel in s.get('panels',[]):
        items = [{'id':panel['id'],'evidence':panel.get('evidence',[])}] + panel.get('elements',[])
        if panel.get('asset') and not panel.get('elements'):
            warnings.append('No element-level evidence map: '+panel['id'])
        for item in items:
            if not item.get('evidence'):
                warnings.append('Missing element evidence: '+item['id'])
            for ref in item.get('evidence',[]):
                if ref not in evidence:
                    errors.append('Unknown evidence '+ref+' in '+item['id'])
            if 'data_ref' in item:
                try:
                    value = P.raw_value(item['data_ref'])
                    expected = item['value']
                    equal = math.isclose(float(value),float(expected),rel_tol=1e-10,abs_tol=1e-12) if finite(expected) else value==expected
                    if not equal:
                        raise ValueError('value differs from actual raw cell')
                except (OSError,KeyError,IndexError,ValueError,TypeError) as ex:
                    errors.append('Data '+item['id']+': '+str(ex))
    if a.svg:
        # Recompose independently from the actual spec/assets to detect stale or altered artwork.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            trial = pathlib.Path(td)/'expected.svg'
            render(argparse.Namespace(spec=a.spec,out=str(trial)))
            warnings.extend(D.read(str(trial)+'.composition.json')['warnings'])
            if trial.read_bytes() != pathlib.Path(a.svg).read_bytes():
                errors.append('Artwork differs from current spec/assets; re-render or inspect unintended changes')
        root = ET.parse(a.svg).getroot()
        ids = [e.get('id') for e in root.iter() if e.get('id')]
        if len(ids)!=len(set(ids)):
            errors.append('Duplicate final SVG IDs')
        by = {e.get('id'):e for e in root.iter() if e.get('id')}
        for panel in s['panels']:
            for item in panel.get('elements',[]):
                actual = panel['id']+'--asset-'+item['id']
                if actual not in by:
                    errors.append('Mapped source element absent from composed SVG: '+actual)
        pt = s.get('font_size',20)*s['width_mm']/s['width']*72/25.4
        if pt < 7:
            warnings.append('Main font is below 7 pt at final size: '+str(pt))
    D.write(a.out,{'status':'failed' if errors else ('needs_review' if warnings else 'mechanically_checked'),
        'errors':errors,'warnings':warnings,'evidence':refs,'science':'not_proven_by_mechanical_checks',
        'layout':'wrap estimates only; inspect rendered PNG/PDF and scaled asset labels'})
    if errors:
        raise ValueError('Checks failed: '+'; '.join(errors))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    subs = p.add_subparsers(dest='command',required=True)
    for name in ['render','check']:
        s = subs.add_parser(name)
        s.add_argument('--spec',required=True)
        s.add_argument('--out',required=True)
        if name=='check':
            s.add_argument('--svg')
    a = p.parse_args()
    try:
        globals()[a.command](a)
    except Exception as ex:
        print(json.dumps({'status':'failed','error':str(ex)},ensure_ascii=False),file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
