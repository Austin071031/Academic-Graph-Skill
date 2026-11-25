#!/usr/bin/env python3
"""Runtime biological graph renderer and checks. Contains no case-specific biology."""
import argparse
import copy
import csv
import hashlib
import json
import math
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
import diagram as D

KINDS = {'activation': 'arrow', 'inhibition': 'bar', 'binding': 'none',
         'association': 'none', 'phosphorylation': 'arrow', 'dephosphorylation': 'arrow',
         'ubiquitination': 'arrow', 'modification': 'arrow', 'recruitment': 'arrow',
         'transport': 'arrow', 'transcription': 'arrow', 'translation': 'arrow',
         'sequence': 'arrow', 'unknown': 'none'}
TYPES = {'gene', 'protein', 'complex', 'family', 'receptor', 'metabolite',
         'cell', 'phenotype', 'process', 'unknown'}
NS = D.NS


def number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def bounds(n):
    return (n['x'], n['y'], n['x'] + n['w'], n['y'] + n['h'])


def overlap(a, b):
    return min(a[2], b[2]) > max(a[0], b[0]) and min(a[3], b[3]) > max(a[1], b[1])


def contains(a, b):
    return a[0] <= b[0] and a[1] <= b[1] and a[2] >= b[2] and a[3] >= b[3]


def route(e, nodes):
    a, b = nodes[e['source']], nodes[e['target']]
    if e.get('points'):
        return e['points']
    dx = b['x'] + b['w']/2 - a['x'] - a['w']/2
    dy = b['y'] + b['h']/2 - a['y'] - a['h']/2
    if dx == 0 and dy == 0:
        raise ValueError('Self-loop or coincident centers require explicit points: ' + e['id'])
    def endpoint(q, vx, vy):
        # Ellipse equation for circular/elliptic entity types.
        if q['type'] in ('metabolite', 'cell'):
            f = 1 / math.sqrt((vx/(q['w']/2))**2 + (vy/(q['h']/2))**2)
        else:
            f = min(q['w']/(2*abs(vx)) if vx else math.inf, q['h']/(2*abs(vy)) if vy else math.inf)
        return [q['x'] + q['w']/2 + vx*f, q['y'] + q['h']/2 + vy*f]
    return [endpoint(a, dx, dy), endpoint(b, -dx, -dy)]


def interpolate(colors, value, domain):
    lo, hi = domain
    if not number(value) or not number(lo) or not number(hi) or hi <= lo:
        raise ValueError('Invalid numeric encoding value/domain')
    if not lo <= value <= hi:
        raise ValueError('Encoding value outside domain; explicitly expand domain, do not clip silently')
    t = (value-lo)/(hi-lo)*(len(colors)-1)
    i = min(int(t), len(colors)-2)
    f = t-i
    a, b = colors[i].lstrip('#'), colors[i+1].lstrip('#')
    rgb = [round(int(a[k:k+2],16)*(1-f)+int(b[k:k+2],16)*f) for k in (0,2,4)]
    return '#' + ''.join('%02x' % v for v in rgb)


def mapped_fill(n, spec):
    enc = spec.get('encoding')
    if not enc:
        return n.get('fill', '#EDF3F6')
    value = n.get('value')
    if value is None:
        return enc.get('missing_color', '#D9DEE3')
    if enc['mode'] == 'categorical':
        cats = enc['categories']
        if str(value) not in cats:
            raise ValueError('Unknown data category: ' + str(value))
        return cats[str(value)]
    return interpolate(enc['colors'], value, enc['domain'])


def validate(s):
    errors, warnings = [], []
    w, h = s.get('width'), s.get('height')
    if not number(w) or not number(h) or w <= 0 or h <= 0:
        return ['Canvas dimensions must be positive finite numbers'], warnings
    items = s.get('nodes', []) + s.get('compartments', []) + s.get('edges', [])
    ids = [v.get('id') for v in items]
    if any(not isinstance(i,str) or not re.fullmatch(r'[A-Za-z_][\w.-]*',i) for i in ids) or len(ids) != len(set(ids)):
        errors.append('Invalid or duplicate semantic IDs')
    # Keep generated IDs collision-free, including suffixes and built-in groups.
    generated = ['compartments','edges','entities','labels','legend','marker-arrow','marker-bar']
    generated += [i + suffix for i in ids if isinstance(i,str) for suffix in ('-shape','-label','-line','-double')]
    if set(ids) & set(generated):
        errors.append('Semantic ID collides with a generated ID')
    by = {v.get('id'): v for v in s.get('nodes', [])}
    regions = {v.get('id'): v for v in s.get('compartments', [])}
    for n in s.get('nodes', []) + s.get('compartments', []):
        if not all(number(n.get(k)) for k in ('x','y','w','h')) or n.get('w',0) <= 0 or n.get('h',0) <= 0:
            errors.append('Invalid geometry: ' + str(n.get('id')))
            continue
        if not contains((0,0,w,h), bounds(n)):
            warnings.append('Outside canvas: ' + n['id'])
        if not n.get('label'):
            errors.append('Missing label: ' + n['id'])
        if not n.get('evidence'):
            warnings.append('Missing evidence references: ' + n['id'])
        if n in s.get('nodes', []):
            if n.get('type') not in TYPES:
                errors.append('Invalid entity type: ' + n['id'])
            c = n.get('compartment')
            if c and c not in regions:
                errors.append('Missing compartment: ' + n['id'])
            elif c and all(number(regions[c].get(k)) for k in ('x','y','w','h')):
                if n.get('type') == 'receptor':
                    if regions[c].get('kind') != 'membrane':
                        warnings.append('Receptor compartment is not a membrane: ' + n['id'])
                    elif not overlap(bounds(n), bounds(regions[c])):
                        warnings.append('Receptor does not intersect membrane: ' + n['id'])
                elif not contains(bounds(regions[c]), bounds(n)):
                    warnings.append('Entity outside assigned compartment: ' + n['id'])
            if n.get('type') == 'unknown':
                warnings.append('Unresolved entity type: ' + n['id'])
    enc = s.get('encoding')
    if enc:
        if enc.get('mode') not in ('categorical','continuous') or not enc.get('label'):
            errors.append('Encoding requires mode and source-derived label/units')
        elif enc['mode'] == 'continuous':
            if len(enc.get('colors', [])) < 2 or len(enc.get('domain', [])) != 2:
                errors.append('Continuous encoding requires colors and domain')
            elif not all(re.fullmatch(r'#[0-9a-fA-F]{6}',c) for c in enc['colors']):
                errors.append('Continuous palette requires six-digit hex colors')
        elif not enc.get('categories'):
            errors.append('Categorical encoding requires a category-color map')
        if not errors:
            for n in s.get('nodes', []):
                try:
                    mapped_fill(n,s)
                except (ValueError, KeyError, TypeError) as ex:
                    errors.append(str(ex) + ': ' + n['id'])
                if n.get('value') is not None and not n.get('data_ref'):
                    warnings.append('Value has no raw cell reference: ' + n['id'])
    for e in s.get('edges', []):
        if e.get('source') not in by or e.get('target') not in by:
            errors.append('Missing endpoint: ' + str(e.get('id')))
            continue
        if e.get('kind') not in KINDS:
            errors.append('Unsupported relation: ' + str(e.get('kind')))
        if not e.get('evidence'):
            warnings.append('Missing evidence references: ' + e['id'])
        if e.get('kind') in ('unknown','association'):
            warnings.append('Review nondirectional/unknown relation: ' + e['id'])
        if e.get('kind') not in ('activation','inhibition','binding','association','sequence','unknown') and not e.get('label'):
            errors.append('Specific process requires a label: ' + e['id'])
        if e.get('bidirectional') and e.get('kind') in ('binding','association','inhibition','unknown'):
            errors.append('Bidirectional relation needs explicit scientifically justified representation: ' + e['id'])
        pts = e.get('points')
        if pts is not None and (len(pts)<2 or any(not isinstance(p,list) or len(p)!=2 or not all(number(x) for x in p) for p in pts)):
            errors.append('Invalid route points: ' + e['id'])
        elif not errors:
            try:
                route(e,by)
            except ValueError as ex:
                errors.append(str(ex))
    for i,a in enumerate(s.get('nodes', [])):
        for b in s.get('nodes', [])[i+1:]:
            if all(number(n.get(k)) for n in (a,b) for k in ('x','y','w','h')) and overlap(bounds(a),bounds(b)):
                warnings.append('Entity boxes overlap; inspect: ' + a['id'] + '/' + b['id'])
    return errors,warnings


def marker(defs, ident, color, bar=False):
    m = D.elem(defs,'marker',id=ident,viewBox='0 0 12 12',refX=14,refY=6,
               markerWidth=6,markerHeight=6,orient='auto',markerUnits='strokeWidth')
    if bar:
        D.elem(m,'path',d='M10,1 L10,11',fill='none',stroke=color,stroke_width=2)
    else:
        D.elem(m,'path',d='M0,1 L10,6 L0,11 Z',fill=color)


def edge_line(parent, e, pts, ident):
    color = '#263746'
    line = D.elem(parent,'polyline',id=ident,points=' '.join('%g,%g' % tuple(p) for p in pts),
                  fill='none',stroke=color,stroke_width=2)
    head = KINDS[e['kind']]
    if head != 'none':
        line.set('marker-end','url(#marker-' + head + ')')
    if e.get('bidirectional'):
        # Separate reverse relation rather than orient-dependent marker-start.
        rev = list(reversed(pts))
        other = D.elem(parent,'polyline',id=ident+'-reverse',points=' '.join('%g,%g'%tuple(p) for p in rev),fill='none',stroke=color,stroke_width=2)
        other.set('marker-end','url(#marker-arrow)')
    if e.get('indirect') or e.get('uncertain') or e['kind']=='unknown':
        line.set('stroke-dasharray','6 4')
        if e.get('bidirectional'):
            other.set('stroke-dasharray','6 4')
    return line


def render(a):
    s = D.read(a.spec)
    errors, warnings = validate(s)
    if errors:
        raise ValueError('\n'.join(errors))
    w,h = s['width'], s['height']
    # Inkscape's actual namespace is used by both this module and diagram.py.
    ET.register_namespace('inkscape',D.INK)
    r = ET.Element('{%s}svg'%NS,{'width':str(s.get('width_mm',180))+'mm',
        'height':str(s.get('height_mm',180*h/w))+'mm','viewBox':'0 0 %g %g'%(w,h),
        'font-family':s.get('font_family','DejaVu Sans, sans-serif')})
    D.elem(r,'title').text=s.get('title','Source-bound biological mechanism')
    D.elem(r,'desc').text='Scientific relationships are specified in the accompanying runtime figure_spec.json and evidence map.'
    D.elem(r,'rect',x=0,y=0,width=w,height=h,fill=s.get('background','#FFFFFF'))
    defs=D.elem(r,'defs')
    marker(defs,'marker-arrow','#263746')
    marker(defs,'marker-bar','#263746',True)
    layers={}
    for name in ('compartments','edges','entities','labels','legend'):
        g=D.elem(r,'g',id=name)
        g.set('{%s}groupmode'%D.INK,'layer')
        g.set('{%s}label'%D.INK,name)
        layers[name]=g
    for c in s.get('compartments',[]):
        g=D.elem(layers['compartments'],'g',id=c['id'],data_kind=c.get('kind','compartment'))
        D.elem(g,'rect',id=c['id']+'-shape',x=c['x'],y=c['y'],width=c['w'],height=c['h'],
               rx=0 if c.get('kind')=='membrane' else 14,fill=c.get('fill','#F4F7FA'),stroke=c.get('stroke','#8496A4'),stroke_width=1.5)
        D.text(g,c['id']+'-label',c['label'],c.get('label_x',c['x']+12),c.get('label_y',c['y']+23),s.get('font_size',16),c.get('label_anchor','start'))
    by={n['id']:n for n in s['nodes']}
    for e in s.get('edges',[]):
        g=D.elem(layers['edges'],'g',id=e['id'],data_source=e['source'],data_target=e['target'],data_kind=e['kind'])
        pts=route(e,by)
        edge_line(g,e,pts,e['id']+'-line')
        if e.get('label'):
            j=(len(pts)-1)//2
            D.text(layers['labels'],e['id']+'-label',e['label'],e.get('label_x',(pts[j][0]+pts[j+1][0])/2),
                   e.get('label_y',(pts[j][1]+pts[j+1][1])/2-10),s.get('font_size',16)*.85)
    for n in s['nodes']:
        g=D.elem(layers['entities'],'g',id=n['id'],data_type=n['type'],data_compartment=n.get('compartment',''))
        if n.get('value') is not None:
            g.set('data-value',json.dumps(n['value'],ensure_ascii=False))
        attrs={'id':n['id']+'-shape','fill':mapped_fill(n,s),'stroke':'#344C60','stroke_width':1.5}
        x,y,nw,nh=n['x'],n['y'],n['w'],n['h']
        typ=n['type']
        if typ in ('metabolite','cell'):
            D.elem(g,'ellipse',cx=x+nw/2,cy=y+nh/2,rx=nw/2,ry=nh/2,**attrs)
        elif typ=='gene':
            D.elem(g,'polygon',points=' '.join('%g,%g'%p for p in [(x+12,y),(x+nw,y),(x+nw-12,y+nh),(x,y+nh)]),**attrs)
        else:
            D.elem(g,'rect',x=x,y=y,width=nw,height=nh,rx=0 if typ in ('process','family') else 9,**attrs)
            if typ=='complex':
                D.elem(g,'rect',id=n['id']+'-double',x=x+4,y=y+4,width=nw-8,height=nh-8,rx=6,fill='none',stroke='#344C60',stroke_width=1)
            elif typ=='family':
                g[-1].set('stroke-dasharray','4 3')
        size=s.get('font_size',16)
        t=D.text(g,n['id']+'-label',n['label'],x+nw/2,y+nh/2+size*.35-(len(n['label'].split('\n'))-1)*size*.625,size)
        if typ=='gene' and n.get('italic',True):
            t.set('font-style','italic')
    # Generate semantic legend from exactly the same primitive/style table as edges.
    used=[]
    for e in s.get('edges',[]):
        key=(e['kind'],bool(e.get('indirect')),bool(e.get('uncertain')),bool(e.get('bidirectional')))
        if key not in used: used.append(key)
    base=s.get('legend_y',h-35-max(len(used)-1,0)*25)
    lx=s.get('legend_x',25)
    for i,(kind,indirect,uncertain,bidir) in enumerate(used):
        y=base+i*25
        e={'kind':kind,'indirect':indirect,'uncertain':uncertain,'bidirectional':bidir}
        edge_line(layers['legend'],e,[[lx,y],[lx+44,y]],'legend-relation-%d'%i)
        label=s.get('relation_labels',{}).get(kind,kind)
        label+=(' / indirect' if indirect else '')+(' / uncertain' if uncertain else '')+(' / bidirectional' if bidir else '')
        D.text(layers['legend'],'legend-relation-label-%d'%i,label,lx+55,y+5,s.get('font_size',16)*.85,'start')
    enc=s.get('encoding')
    if enc:
        ex,ey=enc.get('legend_x',w-280),enc.get('legend_y',base)
        D.text(layers['legend'],'encoding-title',enc['label'],ex,ey-22,s.get('font_size',16)*.85,'start')
        if enc['mode']=='categorical':
            pairs=list(enc['categories'].items())
            for i,(lab,col) in enumerate(pairs):
                D.elem(layers['legend'],'rect',x=ex,y=ey+23*i-12,width=15,height=15,fill=col,stroke='#344C60')
                D.text(layers['legend'],'encoding-label-%d'%i,lab,ex+24,ey+23*i,s.get('font_size',16)*.85,'start')
            missing_y=ey+23*len(pairs)
        else:
            lo,hi=enc['domain']
            for i in range(60):
                D.elem(layers['legend'],'rect',x=ex+i*3,y=ey-12,width=3.1,height=16,fill=interpolate(enc['colors'],lo+(hi-lo)*i/59,[lo,hi]))
            for i,val in enumerate((lo,(lo+hi)/2,hi)):
                D.text(layers['legend'],'encoding-tick-%d'%i,'%g'%val,ex+90*i,ey+23,s.get('font_size',16)*.8)
            missing_y=ey+50
        if any(n.get('value') is None for n in s['nodes']):
            D.elem(layers['legend'],'rect',x=ex,y=missing_y-12,width=15,height=15,fill=enc.get('missing_color','#D9DEE3'))
            D.text(layers['legend'],'encoding-missing','not measured',ex+24,missing_y,s.get('font_size',16)*.85,'start')
    p=pathlib.Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(r).write(str(p),encoding='utf-8',xml_declaration=True)
    D.write(str(p)+'.layout.json',{'warnings':warnings,'status':'needs_review' if warnings else 'model_valid',
        'scientific_review':'not_performed_by_renderer','font_size_pt':s.get('font_size',16)*s.get('width_mm',180)/w*72/25.4})


def source_text(ref):
    p=pathlib.Path(ref['path'])
    if p.suffix.lower()=='.pdf':
        try:
            import fitz
        except ImportError:
            page=ref.get('page')
            if not isinstance(page,int) or page<1:
                raise ValueError('PDF evidence requires 1-based page')
            if D.shutil.which('pdftotext'):
                result=D.cmd_run(['pdftotext','-f',str(page),'-l',str(page),'-layout',str(p),'-'])
                return result.get('stdout') if result.get('returncode')==0 else None
            return None
        with fitz.open(p) as doc:
            if not isinstance(ref.get('page'),int) or not 1 <= ref['page'] <= len(doc):
                raise ValueError('PDF evidence requires 1-based page')
            return doc[ref['page']-1].get_text()
    if p.suffix.lower() in ('.txt','.md','.csv','.tsv','.json','.xml','.svg'):
        return p.read_text(encoding='utf-8-sig')
    return None


def raw_value(ref):
    p=pathlib.Path(ref['path'])
    if D.sha(p)!=ref['sha256']:
        raise ValueError('Raw data hash mismatch: '+str(p))
    if p.suffix.lower() in ('.csv','.tsv'):
        with p.open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f,delimiter=ref.get('delimiter','\t' if p.suffix=='.tsv' else ',')))
        if ref['row']<1:raise ValueError('Data row is 1-based excluding header')
        v=rows[ref['row']-1][ref['column']]
    elif p.suffix.lower()=='.json':
        v=D.read(p)
        for key in ref['keys']:v=v[key]
    else:
        raise ValueError('Raw-cell helper supports CSV/TSV/JSON; independently verify other formats')
    return v


def check(a):
    s=D.read(a.spec);errors,warnings=validate(s)
    evidence=s.get('evidence',{})
    evidence_checks=[]
    for ident,ref in evidence.items():
        row={'id':ident,'quote_check':'not_checked'}
        try:
            if D.sha(ref['path'])!=ref['sha256']:raise ValueError('Source hash mismatch')
            if not ref.get('locator') and not ref.get('page'):raise ValueError('Missing source locator')
            txt=source_text(ref)
            if ref.get('quote') and txt is not None:
                norm=lambda t:re.sub(r'\s+',' ',t).strip()
                if norm(ref['quote']) not in norm(txt):raise ValueError('Quote not found in actual source')
                row['quote_check']='found_literal_not_semantic_validation'
            elif ref.get('quote'):
                warnings.append('Quote text extraction unavailable: '+ident)
            else:
                warnings.append('No supporting quote; review visual/data locator: '+ident)
            row['source_hash']='matches'
        except (OSError,ValueError,KeyError) as ex:
            errors.append('Evidence '+ident+': '+str(ex))
        evidence_checks.append(row)
    for item in s.get('nodes',[])+s.get('edges',[])+s.get('compartments',[]):
        for ref in item.get('evidence',[]):
            if ref not in evidence:errors.append('Unknown evidence ID '+ref+' for '+item['id'])
        if 'data_ref' in item:
            try:
                value=raw_value(item['data_ref'])
                expected=item.get('value')
                if isinstance(expected,(int,float)) and not isinstance(expected,bool):
                    if not math.isclose(float(value),expected,rel_tol=1e-12,abs_tol=1e-12):raise ValueError('Value differs from raw cell')
                elif value!=expected:raise ValueError('Value differs from raw cell')
            except (OSError,ValueError,KeyError,IndexError,TypeError) as ex:
                errors.append('Data '+item['id']+': '+str(ex))
    if a.svg:
        root=ET.parse(a.svg).getroot();idx={n.get('id'):n for n in root.iter() if n.get('id')}
        ids=[n.get('id') for n in root.iter() if n.get('id')]
        if len(ids)!=len(set(ids)):errors.append('Duplicate SVG IDs')
        for n in s.get('nodes',[]):
            g=idx.get(n['id']);label=idx.get(n['id']+'-label');shape=idx.get(n['id']+'-shape')
            if g is None or label is None or shape is None:
                errors.append('Missing editable node elements: '+n['id']);continue
            if ''.join(label.itertext())!=n['label'].replace('\n',''):errors.append('SVG label mismatch: '+n['id'])
            if shape.get('fill','').lower()!=mapped_fill(n,s).lower():errors.append('SVG encoding mismatch: '+n['id'])
            if g.get('data-type')!=n['type'] or g.get('data-compartment','')!=n.get('compartment',''):
                errors.append('SVG entity metadata mismatch: '+n['id'])
        for e in s.get('edges',[]):
            line=idx.get(e['id']+'-line');g=idx.get(e['id'])
            if line is None or g is None:errors.append('Missing edge '+e['id']);continue
            if any(g.get('data-'+k)!=e[k] for k in ('source','target','kind')):errors.append('SVG edge metadata mismatch: '+e['id'])
            head=KINDS.get(e['kind'],'none');expected='url(#marker-'+head+')' if head!='none' else None
            if line.get('marker-end')!=expected:errors.append('SVG edge target marker mismatch: '+e['id'])
            pts=route(e,{n['id']:n for n in s['nodes']})
            actual=[list(map(float,p.split(','))) for p in line.get('points','').split()]
            if len(actual)!=len(pts) or any(not math.isclose(x,y,rel_tol=1e-5,abs_tol=1e-5) for p,q in zip(actual,pts) for x,y in zip(p,q)):
                errors.append('SVG route mismatch: '+e['id'])
            if bool(line.get('stroke-dasharray')) != bool(e.get('indirect') or e.get('uncertain') or e['kind']=='unknown'):
                errors.append('SVG evidence style mismatch: '+e['id'])
            target=next(n for n in s['nodes'] if n['id']==e['target'])
            x,y,x2,y2=bounds(target);px,py=pts[-1]
            if target['type'] in ('metabolite','cell'):
                boundary_error=abs(((px-(x+x2)/2)/(target['w']/2))**2+((py-(y+y2)/2)/(target['h']/2))**2-1)>0.1
            else:
                boundary_error=not(x-2<=px<=x2+2 and y-2<=py<=y2+2 and min(abs(px-x),abs(px-x2),abs(py-y),abs(py-y2))<=2)
            if boundary_error:warnings.append('Route does not end at target boundary: '+e['id'])
            # Check all non-endpoint nodes for segment intersections, including routed edges.
            for n in s['nodes']:
                if n['id'] in (e['source'],e['target']):continue
                if any(segment_box(p,q,bounds(n)) for p,q in zip(pts,pts[1:])):
                    warnings.append('Edge crosses unrelated entity: '+e['id']+'/'+n['id'])
        for n in s.get('nodes',[])+s.get('compartments',[]):
            shape=idx.get(n['id']+'-shape')
            if shape is None:
                errors.append('Missing shape '+n['id']);continue
            tag=shape.tag.rsplit('}',1)[-1]
            if tag=='rect':
                expected={'x':n['x'],'y':n['y'],'width':n['w'],'height':n['h']}
            elif tag=='ellipse':
                expected={'cx':n['x']+n['w']/2,'cy':n['y']+n['h']/2,'rx':n['w']/2,'ry':n['h']/2}
            else:expected={}
            for k,v in expected.items():
                if not math.isclose(float(shape.get(k,'nan')),v,rel_tol=1e-9,abs_tol=1e-9):errors.append('SVG geometry mismatch '+n['id']+'/'+k)
        for ident,d in [('marker-bar','M10,1 L10,11'),('marker-arrow','M0,1 L10,6 L0,11 Z')]:
            m=idx.get(ident)
            if m is None or len(m)!=1 or m[0].get('d')!=d or m.get('refX')!='14' or m.get('orient')!='auto':
                errors.append('Marker definition mismatch '+ident)
        if 'legend' not in idx:errors.append('Missing legend layer')
        if s.get('encoding'):
            label=idx.get('encoding-title')
            if label is None or ''.join(label.itertext())!=s['encoding']['label']:errors.append('Encoding legend label mismatch')
        for el in root.iter():
            if el.tag.rsplit('}',1)[-1]=='image':warnings.append('Raster/image present; inspect editable content')
    out={'status':'failed' if errors else 'needs_review' if warnings else 'mechanical_checks_passed',
        'errors':errors,'warnings':warnings,'evidence_checks':evidence_checks,
        'scientific_interpretation':'requires_agent_review_against_primary_sources',
        'visual_inspection':'not_performed_by_checker'}
    D.write(a.out,out)
    if errors:raise ValueError('Mechanical validation failed; see '+a.out)


def segment_box(p,q,box):
    # Liang-Barsky segment/rectangle intersection, independent of SVG metadata.
    x0,y0,x1,y1=box;dx=q[0]-p[0];dy=q[1]-p[1];lo,hi=0.,1.
    for a,b in ((-dx,p[0]-x0),(dx,x1-p[0]),(-dy,p[1]-y0),(dy,y1-p[1])):
        if a==0:
            if b<=0:return False
        else:
            t=b/a
            if a<0:lo=max(lo,t)
            else:hi=min(hi,t)
    return lo<hi


def fingerprint(e):
    # Local element content; avoid falsely marking every parent of an edit as changed.
    return {'tag':e.tag,'attrs':dict(sorted(e.attrib.items())),'text':e.text or '',
            'tail':e.tail or '', 'children':[ET.tostring(c,encoding='unicode') if not c.get('id') else {'id':c.get('id'),'tag':c.tag} for c in e]}


def diff(a):
    before=ET.parse(a.before).getroot();after=ET.parse(a.after).getroot()
    def index(root):
        idx={}
        for e in root.iter():
            if e.get('id'):
                if e.get('id') in idx:raise ValueError('Duplicate source ID')
                idx[e.get('id')]=e
        return idx
    b,c=index(before),index(after)
    changed=sorted(k for k in b.keys() & c.keys() if fingerprint(b[k])!=fingerprint(c[k]))
    removed=sorted(b.keys()-c.keys());added=sorted(c.keys()-b.keys())
    allowed=set(D.read(a.allowed)) if a.allowed else set()
    unexpected=sorted((set(changed)|set(removed)|set(added))-allowed)
    # Root anonymous geometry/style/children must be preserved too.
    root_changed=fingerprint(before)!=fingerprint(after)
    D.write(a.out,{'original_sha256':D.sha(a.before),'revised_sha256':D.sha(a.after),
        'changed_ids':changed,'removed_ids':removed,'added_ids':added,'unexpected_ids':unexpected,
        'unchanged_id_count':len(b.keys() & c.keys())-len(changed),'root_local_changed':root_changed,
        'status':'needs_review' if unexpected or root_changed else 'id_scope_matches',
        'limits':'ID/local subtree comparison, not pixel equality, CSS inheritance proof or biological validation',
        'human_confirmation':'not_performed'})


def main():
    p=argparse.ArgumentParser(description=__doc__);subs=p.add_subparsers(dest='command',required=True)
    for command,keys in [('render',['spec','out']),('check',['spec','out']),('diff',['before','after','out'])]:
        q=subs.add_parser(command)
        for k in keys:q.add_argument('--'+k,required=True)
        if command=='check':q.add_argument('--svg')
        if command=='diff':q.add_argument('--allowed',help='JSON list of source IDs allowed to change/add/remove')
    a=p.parse_args()
    try:globals()[a.command](a)
    except Exception as ex:
        print(json.dumps({'status':'failed','error':str(ex)},ensure_ascii=False),file=sys.stderr);return 1
    print(json.dumps({'status':'completed','output':a.out},ensure_ascii=False));return 0

if __name__=='__main__':sys.exit(main())
