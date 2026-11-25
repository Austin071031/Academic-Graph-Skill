#!/usr/bin/env python3
"""Source-bound chart renderer. v2.0.0 binds error-bar meaning to a source column."""
import argparse
import csv
import hashlib
import json
import math
import pathlib
import shutil
import sys
import warnings
import xml.etree.ElementTree as ET


def load(p):
    return json.loads(pathlib.Path(p).read_text(encoding='utf-8'))


def save(p, obj):
    p = pathlib.Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    tmp.replace(p)


def digest(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def table(path, sheet=0):
    p = pathlib.Path(path)
    if p.suffix.lower() in ('.xlsx', '.xlsm'):
        import openpyxl
        wb = openpyxl.load_workbook(p, read_only=True, data_only=True)
        ws = wb.worksheets[sheet] if isinstance(sheet, int) else wb[sheet]
        values = list(ws.values)
        headers = [str(v) if v is not None else '' for v in values[0]]
        rows = [dict(zip(headers, r)) for r in values[1:]]
        loc = {'sheet': ws.title, 'row_numbering': 'Excel rows, header=1, first data=2'}
        wb.close()
    elif p.suffix.lower() == '.json':
        rows = load(p)
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            raise ValueError('JSON table must be a list of row objects')
        headers = list(rows[0]) if rows else []
        loc = {'row_numbering': 'JSON row array index + 2; index=row-2'}
    else:
        with p.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t' if p.suffix.lower() == '.tsv' else ',')
            headers = reader.fieldnames or []
            rows = list(reader)
        loc = {'row_numbering': 'logical table rows, header=1, first data=2 (not physical lines for multiline CSV)'}
    if not headers or len(headers) != len(set(headers)) or '' in headers:
        raise ValueError('Missing/duplicate column headers')
    if any(set(r) != set(headers) for r in rows):
        raise ValueError('Ragged table rows')
    return headers, rows, loc


def single_token(src, data, column, what):
    if column not in src['headers']:
        raise ValueError('Missing %s column: %s' % (what, column))
    found = []
    for rn, row in data:
        token = str(row[column]).strip()
        if not token:
            raise ValueError('Blank %s at row %s' % (what, rn))
        found.append(token)
    if len(set(found)) != 1:
        raise ValueError('Selected rows disagree on %s' % what)
    return found[0]


def series_identity(desc, src, data, fallback_label, fallback_color):
    # One selected pair from the table replaces a conflicting spec label or color.
    label_col = desc.get('label_column')
    color_col = desc.get('color_column')
    if not label_col and not color_col:
        return fallback_label, fallback_color
    if not label_col or not color_col:
        raise ValueError('label_column and color_column must both be set')
    for col in (label_col, color_col):
        if col not in src['headers']:
            raise ValueError('Missing legend column: ' + col)
    pairs = []
    for rn, row in data:
        label = str(row[label_col]).strip()
        color = str(row[color_col]).strip()
        if not label or not color:
            raise ValueError('Blank series label or color at row %s' % rn)
        pairs.append((label, color))
    if len(set(pairs)) != 1:
        raise ValueError('Selected rows disagree on series label or color')
    return pairs[0]


def number(v, context):
    # Do not remove punctuation, assume units, impute, or convert missing values to zero.
    if isinstance(v, bool) or v is None or str(v).strip() == '':
        raise ValueError('Missing/non-numeric value at ' + context)
    x = float(v)
    if not math.isfinite(x):
        raise ValueError('Non-finite value at ' + context)
    return x


def resolve_tables(spec, base):
    sources = {}
    for ident, d in spec['sources'].items():
        p = pathlib.Path(d['path'])
        p = p if p.is_absolute() else base / p
        p = p.resolve()
        headers, rows, loc = table(p, d.get('sheet', 0))
        sources[ident] = {'path': str(p), 'sha256': digest(p), 'headers': headers, 'rows': rows, **loc}
    return sources


def render(spec_path, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    import numpy as np
    from PIL import Image
    spec_path = pathlib.Path(spec_path).resolve()
    spec = load(spec_path)
    sources = resolve_tables(spec, spec_path.parent)
    out = pathlib.Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    panels = spec['panels']
    if not panels:
        raise ValueError('At least one panel is required')
    style = spec.get('style', {})
    cols = int(style.get('columns', min(2, len(panels))))
    if cols < 1:
        raise ValueError('columns must be positive')
    rows = math.ceil(len(panels) / cols)
    width = float(style.get('width_mm', 180)) / 25.4
    height = float(style.get('height_mm', 70 * rows)) / 25.4
    dpi = int(style.get('dpi', 300))
    if min(width, height, dpi) <= 0:
        raise ValueError('Invalid physical size or DPI')
    plt.rcParams.update({'svg.fonttype': 'none', 'svg.hashsalt': 'source-bound-charts-v1',
                         'pdf.fonttype': 42, 'ps.fonttype': 42, 'font.size': style.get('font_size', 9),
                         'axes.linewidth': style.get('line_width', .8), 'axes.spines.top': False,
                         'axes.spines.right': False, 'savefig.transparent': style.get('transparent', False)})
    font_path = style.get('font_path')
    if font_path:
        fp = pathlib.Path(font_path)
        fp = fp if fp.is_absolute() else spec_path.parent / fp
        font_manager.fontManager.addfont(str(fp))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(fp)).get_name()
    else:
        plt.rcParams['font.family'] = style.get('font_family', ['DejaVu Sans'])
    palette = style.get('palette', ['#0072B2', '#D55E00', '#009E73', '#CC79A7', '#E69F00', '#56B4E9'])
    if not palette:
        raise ValueError('Empty palette')
    fig, axes = plt.subplots(rows, cols, figsize=(width, height), squeeze=False, constrained_layout=True)
    mapping, checks, issues, series_registry = [], [], [], []
    error_kind_annotations = []
    counter = [0]
    def gid(prefix):
        counter[0] += 1
        return '%s-%06d' % (prefix, counter[0])
    def selected(desc):
        src = sources[desc['source']]
        for col in [desc.get('x'), desc.get('y'), desc.get('error'), desc.get('error_low'), desc.get('error_high')]:
            if col and col not in src['headers']:
                raise ValueError('Missing column: ' + col)
        filt = desc.get('where', {})
        if not set(filt).issubset(src['headers']):
            raise ValueError('Unknown filter column')
        ids = desc.get('rows')
        if ids is not None and (len(ids) != len(set(ids)) or any(not isinstance(i, int) or i < 2 or i > len(src['rows'])+1 for i in ids)):
            raise ValueError('Invalid/duplicate logical row selection')
        result = [(i+2, r) for i, r in enumerate(src['rows']) if (ids is None or i+2 in ids) and all(str(r[k]) == str(v) for k, v in filt.items())]
        if not result:
            raise ValueError('Selection has no rows')
        if desc.get('sort_by'):
            key = desc['sort_by']
            if key not in src['headers']:
                raise ValueError('Unknown sort column')
            result.sort(key=lambda pair: number(pair[1][key], key))
        return src, result
    def cell(src, row, col, value):
        return {'file': src['path'], 'sha256': src['sha256'], 'sheet': src.get('sheet'), 'row': row, 'column': col, 'raw_value': value}
    def record(ident, panel, series, marks, values, geometry):
        mapping.append({'element_id': ident, 'panel': panel, 'series': series, 'source_cells': marks,
                        'values': values, 'geometry': geometry})
    def check(name, condition, detail):
        checks.append({'check': name, 'passed': bool(condition), 'detail': detail})
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for pi, panel in enumerate(panels):
            ax = axes.flat[pi]
            ax.set_gid('panel-%d' % pi)
            kind = panel['kind']
            if kind not in ['bar', 'line', 'scatter', 'box', 'heatmap', 'pie']:
                raise ValueError('Unsupported chart kind; implement source-bound custom plotting: ' + kind)
            descriptors = panel.get('series', [])
            if not descriptors:
                raise ValueError('Panel needs series')
            category_reference = None
            for si, desc in enumerate(descriptors):
                src, data = selected(desc)
                ycol = desc['y']
                y = np.zeros(len(data)) if kind == 'heatmap' else np.array([number(r[ycol], '%s:%s:%s' % (src['path'], rn, ycol)) for rn, r in data])
                label = desc.get('label', ycol)
                color = desc.get('color', palette[si % len(palette)])
                label, color = series_identity(desc, src, data, label, color)
                series_registry.append({'panel': pi, 'series': si, 'label': label, 'color': color, 'source': desc['source'], 'y': ycol, 'value': desc.get('value'), 'where': desc.get('where', {})})
                errcols = [desc.get('error_low'), desc.get('error_high')] if desc.get('error_low') or desc.get('error_high') else ([desc['error']] if desc.get('error') else [])
                if desc.get('error_kind_column') and not errcols:
                    raise ValueError('error_kind_column requires error distance columns')
                if errcols and desc.get('error_kind_column'):
                    error_kind = single_token(src, data, desc['error_kind_column'], 'error kind')
                else:
                    error_kind = desc.get('error_kind')
                if errcols and not error_kind:
                    raise ValueError('Error bars require error_kind or error_kind_column read from source: SD/SEM/CI/etc.')
                if any(c is None for c in errcols):
                    raise ValueError('Both asymmetric error columns are required; values are nonnegative distances')
                err = np.array([[number(r[c], c) for _, r in data] for c in errcols]) if errcols else None
                if err is not None and kind not in ['bar', 'line', 'scatter']:
                    raise ValueError('Error columns unsupported for this chart kind; use source-bound custom plot')
                if err is not None and (err < 0).any():
                    raise ValueError('Negative error distance; convert documented endpoints in a traced preprocessing step')
                if err is not None and len(errcols) == 1:
                    err = err[0]
                xcol = desc.get('x')
                rawx = [r[xcol] for _, r in data] if xcol else list(range(len(y)))
                if kind in ['bar', 'box', 'pie'] or desc.get('categorical_x'):
                    labels = [str(v) for v in rawx]
                    if kind != 'box' and len(set(labels)) != len(labels):
                        raise ValueError('Duplicate categories need explicit aggregation or different grouping')
                    if kind == 'bar' and category_reference is not None and labels != category_reference:
                        raise ValueError('Grouped bar category ordering differs between series')
                    category_reference = labels
                    x = np.arange(len(y), dtype=float)
                else:
                    x = np.zeros(len(data)) if kind == 'heatmap' else np.array([number(v, xcol or 'row index') for v in rawx])
                if kind in ['bar', 'line', 'scatter']:
                    if panel.get('xscale') == 'log' and (x <= 0).any():
                        raise ValueError('Logarithmic x axis requires positive coordinates')
                    if panel.get('yscale') == 'log':
                        if kind == 'bar':
                            raise ValueError('Logarithmic bars need an explicitly justified positive baseline in a custom plot')
                        lower = y if err is None else y - (err[0] if err.ndim == 2 else err)
                        if (lower <= 0).any():
                            raise ValueError('Logarithmic y axis requires positive values and error bounds')
                    error_artist = None
                    if kind == 'bar':
                        w = .8 / len(descriptors)
                        xp = x + (si - (len(descriptors)-1)/2) * w
                        artist = ax.bar(xp, y, w, yerr=err, label=label, color=color, capsize=3, edgecolor='black', linewidth=.4)
                        ax.set_xticks(x, labels, rotation=panel.get('label_rotation', 0))
                        error_artist = artist.errorbar
                    elif kind == 'line':
                        artist = ax.errorbar(x, y, yerr=err, label=label, color=color, marker=desc.get('marker', 'o'), linewidth=style.get('line_width', 1.2), capsize=3)
                    else:
                        artist = ax.scatter(x, y, label=label, color=color, s=desc.get('point_size', 18))
                        if err is not None:
                            error_artist = ax.errorbar(x, y, yerr=err, fmt='none', ecolor=color, capsize=3)
                    if kind == 'line':
                        error_artist = artist
                        artist.lines[0].set_gid('panel-%d-series-%d' % (pi, si))
                        check('line_data', np.allclose(artist.lines[0].get_ydata(), y) and np.allclose(artist.lines[0].get_xdata(), x), label)
                    elif kind == 'scatter':
                        artist.set_gid('panel-%d-series-%d' % (pi, si))
                        check('scatter_data', np.allclose(artist.get_offsets(), np.column_stack((x, y))), label)
                    if err is not None:
                        segments = error_artist.lines[2][0].get_segments()
                        error_artist.lines[2][0].set_gid('panel-%d-series-%d-errors' % (pi, si))
                        low, high = (err[0], err[1]) if err.ndim == 2 else (err, err)
                        xerr = xp if kind == 'bar' else x
                        expected_segments = [[[float(xerr[j]), float(y[j]-low[j])], [float(xerr[j]), float(y[j]+high[j])]] for j in range(len(y))]
                        check('errorbar_geometry', np.allclose(segments, expected_segments), {'series': label, 'error_kind': error_kind})
                    if err is not None and desc.get('error_kind_column'):
                        error_id = 'panel-%d-series-%d-error-kind' % (pi, si)
                        error_text = 'Error: ' + error_kind
                        error_artist = ax.text(.99, .96, error_text, transform=ax.transAxes, ha='right', va='top', fontsize=style.get('font_size', 9))
                        error_artist.set_gid(error_id)
                        error_cells = [cell(src, rn, desc['error_kind_column'], r[desc['error_kind_column']]) for rn, r in data]
                        record(error_id, pi, si, error_cells, {'error_kind': error_kind, 'display_text': error_text}, {'type': 'native_text'})
                        error_kind_annotations.append(error_id)
                    for j, (rn, r) in enumerate(data):
                        ident = gid('data')
                        if kind == 'bar':
                            patch = artist.patches[j]
                            patch.set_gid(ident)
                            measured = float(patch.get_height())
                            check('bar_height', math.isclose(measured, y[j], rel_tol=1e-12, abs_tol=1e-12), ident)
                            geom = {'x_center': float(xp[j]), 'height': measured, 'baseline': 0}
                        else:
                            # SVG group represents a series; point index disambiguates individual marks.
                            geom = {'svg_group': 'panel-%d-series-%d' % (pi, si), 'point_index': j, 'x': float(x[j]), 'y': float(y[j])}
                            ident = geom['svg_group'] + ':point-' + str(j)
                        marks = [cell(src, rn, ycol, r[ycol])]
                        if xcol:
                            marks.append(cell(src, rn, xcol, r[xcol]))
                        marks.extend(cell(src, rn, c, r[c]) for c in errcols)
                        record(ident, pi, si, marks, {'x': rawx[j], 'y': float(y[j]), 'error': None if err is None else (err[:, j].tolist() if err.ndim == 2 else float(err[j])), 'error_kind': error_kind}, geom)
                    if desc.get('categorical_x'):
                        ax.set_xticks(x, [str(v) for v in rawx], rotation=panel.get('label_rotation', 0))
                elif kind == 'box':
                    groups = list(dict.fromkeys(str(v) for v in rawx))
                    values = [[float(y[j]) for j, v in enumerate(rawx) if str(v) == g] for g in groups]
                    # Do not accept precomputed quartiles masquerading as observations.
                    boxes = ax.boxplot(values, positions=np.arange(len(groups))+1+si*.25, widths=.2 if len(descriptors)>1 else .5,
                                       whis=panel.get('whis', 1.5), patch_artist=True)
                    for j, g in enumerate(groups):
                        ident = gid('box')
                        boxes['boxes'][j].set_gid(ident)
                        boxes['boxes'][j].set_facecolor(color)
                        inds = [k for k, v in enumerate(rawx) if str(v) == g]
                        record(ident, pi, si, [cell(src, data[k][0], ycol, data[k][1][ycol]) for k in inds],
                               {'category': g, 'n': len(values[j]), 'observations': values[j]}, {'whis': panel.get('whis', 1.5), 'quartile_method': 'matplotlib/numpy default percentiles'})
                    ax.set_xticks(np.arange(len(groups))+1, groups)
                elif kind == 'pie':
                    if len(descriptors) != 1 or (y < 0).any() or y.sum() <= 0:
                        raise ValueError('Pie requires one nonnegative positive-total series')
                    wedges, _ = ax.pie(y, labels=[str(v) for v in rawx], startangle=panel.get('startangle', 90), colors=palette)
                    for j, wedge in enumerate(wedges):
                        ident = gid('sector'); wedge.set_gid(ident)
                        angle = float(wedge.theta2-wedge.theta1)
                        check('sector_angle', abs(angle - float(y[j]/y.sum()*360)) < 1e-3, ident)
                        rn, r = data[j]
                        record(ident, pi, si, [cell(src, rn, ycol, r[ycol])] + ([cell(src, rn, xcol, r[xcol])] if xcol else []), {'value': float(y[j]), 'total': float(y.sum()), 'category': str(rawx[j])}, {'degrees': angle})
                elif kind == 'heatmap':
                    if len(descriptors) != 1:
                        raise ValueError('Heatmap requires one series with x, y, value columns in long form')
                    xc, yc, vc = desc['x'], desc['y'], desc['value']
                    if vc not in src['headers']:
                        raise ValueError('Missing heatmap value column')
                    xs = list(dict.fromkeys(str(r[xc]) for _, r in data))
                    ys = list(dict.fromkeys(str(r[yc]) for _, r in data))
                    mat = np.full((len(ys), len(xs)), np.nan)
                    for rn, r in data:
                        ix, iy = xs.index(str(r[xc])), ys.index(str(r[yc]))
                        if np.isfinite(mat[iy, ix]):
                            raise ValueError('Duplicate heatmap coordinate')
                        val = number(r[vc], vc); mat[iy, ix] = val
                        record('panel-%d-heatmap:cell-%d-%d' % (pi, iy, ix), pi, si, [cell(src, rn, c, r[c]) for c in [xc, yc, vc]], {'value': val, 'x': str(r[xc]), 'y': str(r[yc])}, {'row': iy, 'column': ix})
                    if np.isnan(mat).any():
                        raise ValueError('Incomplete heatmap grid; explicitly handle missing cells in custom plot')
                    mesh = ax.pcolormesh(np.arange(len(xs)+1), np.arange(len(ys)+1), mat, cmap=panel.get('cmap', 'viridis'), vmin=panel.get('vmin'), vmax=panel.get('vmax'), rasterized=False)
                    mesh.set_gid('panel-%d-heatmap' % pi)
                    ax.set_xticks(np.arange(len(xs))+.5, xs); ax.set_yticks(np.arange(len(ys))+.5, ys); ax.invert_yaxis()
                    fig.colorbar(mesh, ax=ax, label=panel.get('colorbar_label', vc))
                    check('heatmap_values', np.allclose(np.asarray(mesh.get_array()).reshape(mat.shape), mat), vc)
            ax.set_xlabel(panel.get('xlabel', ''))
            ax.set_ylabel(panel.get('ylabel', ''))
            ax.set_title(panel.get('title', ''), loc='left', fontweight='bold')
            for axis in ['x', 'y']:
                if axis+'scale' in panel:
                    getattr(ax, 'set_'+axis+'scale')(panel[axis+'scale'])
                if axis+'lim' in panel:
                    getattr(ax, 'set_'+axis+'lim')(panel[axis+'lim'])
            if kind == 'bar' and 'ylim' not in panel:
                ax.margins(y=.15)
            if kind in ['bar', 'line', 'scatter']:
                ymin, ymax = ax.get_ylim()
                for m in [v for v in mapping if v.get('panel') == pi and 'y' in v.get('values', {})]:
                    if not ymin <= m['values']['y'] <= ymax:
                        issues.append({'kind': 'data_clipped', 'element_id': m['element_id']})
                if kind == 'bar' and not ymin <= 0 <= ymax:
                    issues.append({'kind': 'bar_baseline_truncated', 'ylim': [ymin, ymax]})
            if kind in ['line', 'scatter', 'bar'] and panel.get('legend', True):
                ax.legend(frameon=False, loc=panel.get('legend_loc', 'best'))
            for anno in panel.get('annotations', []):
                if not anno.get('source'):
                    raise ValueError('Annotation needs actual source locator; never invent significance/n')
                annotation_id = 'panel-%d-annotation-%d' % (pi, len(mapping))
                annotation_artist = ax.text(anno['x'], anno['y'], anno['text'], ha=anno.get('ha', 'center'), va=anno.get('va', 'bottom'), fontsize=anno.get('fontsize', style.get('font_size', 9)))
                annotation_artist.set_gid(annotation_id)
                mapping.append({'element_id': annotation_id, 'panel': pi, 'annotation': anno, 'source_cells': []})
        for ax in list(axes.flat)[len(panels):]:
            ax.set_visible(False)
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        bounds = fig.bbox
        audit_texts = []
        for ax in fig.axes:
            audit_texts.extend([ax.title, ax._left_title, ax._right_title, ax.xaxis.label, ax.yaxis.label, ax.xaxis.get_offset_text(), ax.yaxis.get_offset_text()])
            audit_texts.extend(ax.texts)
            if ax.get_legend():
                audit_texts.extend(ax.get_legend().get_texts())
            for axis_obj, limits in [(ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())]:
                lo, hi = sorted(limits)
                for tick in axis_obj.get_major_ticks() + axis_obj.get_minor_ticks():
                    if lo <= tick.get_loc() <= hi:
                        audit_texts.extend([tick.label1, tick.label2])
        for t in audit_texts:
            if not t.get_visible() or not t.get_text():
                continue
            box = t.get_window_extent(renderer)
            if box.x0 < bounds.x0-1 or box.y0 < bounds.y0-1 or box.x1 > bounds.x1+1 or box.y1 > bounds.y1+1:
                issues.append({'kind': 'text_outside_canvas', 'text': t.get_text()})
        # No bbox_inches=tight: physical dimensions are part of the output contract.
        name = spec.get('name', 'figure')
        if pathlib.Path(name).name != name:
            raise ValueError('name must be a basename')
        files = {}
        for fmt in ['svg', 'png', 'pdf']:
            p = out / (name + '.' + fmt)
            fig.savefig(p, dpi=dpi, format=fmt, transparent=style.get('transparent', False))
            files[fmt] = {'path': str(p), 'sha256': digest(p), 'bytes': p.stat().st_size}
        plt.close(fig)
        font_warnings = sorted(set(str(w.message) for w in caught if 'Glyph' in str(w.message)))
        issues.extend({'kind': 'missing_glyph', 'detail': w} for w in font_warnings)
    with Image.open(files['png']['path']) as im:
        im.load()
        files['png'].update({'pixels': list(im.size), 'dpi': im.info.get('dpi'), 'mode': im.mode})
        expected = [int(width*dpi), int(height*dpi)]
        check('png_physical_size', all(abs(a-b)<=1 for a,b in zip(im.size, expected)), {'expected': expected, 'actual': list(im.size)})
    root = ET.parse(files['svg']['path']).getroot()
    text_count = sum(e.tag.endswith('}text') for e in root.iter())
    check('editable_svg_text', text_count > 0, text_count)
    svg_ids = {e.get('id') for e in root.iter() if e.get('id')}
    for item in mapping:
        base_id = item['element_id'].split(':')[0]
        check('element_id_exists', base_id in svg_ids, item['element_id'])
    check('real_pdf', pathlib.Path(files['pdf']['path']).read_bytes().startswith(b'%PDF-'), files['pdf']['path'])
    source_metadata = {k: {key: value for key, value in v.items() if key != 'rows'} for k, v in sources.items()}
    save(out/'source_map.json', {'version': '1.0.0', 'sources': source_metadata, 'elements': mapping, 'series_registry': series_registry, 'error_kind_annotations': error_kind_annotations,
                                'reverse_index': {k: [m['element_id'] for m in mapping if any(c['file']==v['path'] for c in m.get('source_cells', []))] for k,v in sources.items()}})
    shutil.copyfile(spec_path, out/'plot_spec.json') if spec_path != out/'plot_spec.json' else None
    save(out/'export_checks.json', {'status': 'passed' if all(c['passed'] for c in checks) and not issues else 'needs_review',
         'checks': checks, 'issues': issues, 'exports': files, 'font_family': plt.rcParams['font.family'],
         'style': style, 'runtime': {'python': sys.version, 'matplotlib': matplotlib.__version__, 'numpy': np.__version__},
         'limits': ['Geometry audit does not prove scientific interpretation or absence of all label overlaps.', 'PDF font embedding/color profile require external inspection if specified.'],
         'human_confirmation': 'not_performed'})
    return {'exports': files, 'mapping_count': len(mapping), 'issues': issues, 'checks_passed': sum(c['passed'] for c in checks), 'checks_failed': sum(not c['passed'] for c in checks)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='cmd', required=True)
    q = sub.add_parser('inspect'); q.add_argument('--source', required=True); q.add_argument('--sheet', default='0'); q.add_argument('--out', required=True)
    q = sub.add_parser('render'); q.add_argument('--spec', required=True); q.add_argument('--out', required=True)
    a = p.parse_args()
    try:
        if a.cmd == 'inspect':
            h, r, loc = table(a.source, int(a.sheet) if a.sheet.isdigit() else a.sheet)
            report = {'path': str(pathlib.Path(a.source).resolve()), 'sha256': digest(a.source), 'columns': h, 'row_count': len(r), 'rows': [{'row': i+2, 'values': row} for i,row in enumerate(r)], **loc}
            save(a.out, report); print(json.dumps({'out': a.out, 'row_count': len(r)}))
        else:
            print(json.dumps(render(a.spec, a.out), ensure_ascii=False))
        return 0
    except Exception as e:
        print(json.dumps({'status': 'failed', 'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
