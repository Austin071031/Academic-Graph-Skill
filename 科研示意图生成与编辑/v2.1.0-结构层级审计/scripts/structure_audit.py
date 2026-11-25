#!/usr/bin/env python3
"""Mechanical consistency checks for an authored figure spec and its SVG.

This helper does not inspect scientific sources and cannot validate mechanism,
causality, or whether an authored edge direction is supported by evidence.
"""
import argparse
import hashlib
import json
import math
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

VERSION = '2.1.0'
LAYERS = ['compartments', 'edges', 'entities', 'labels', 'legend']
DIRECTED_KINDS = {'activation', 'sequence', 'arrow'}
SUPPORTED_KINDS = DIRECTED_KINDS | {'inhibition', 'association'}
NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
NUMBER_RE = re.compile(NUMBER)
LENGTH_RE = re.compile(r'^\s*(' + NUMBER + r')\s*(?:px)?\s*$')
MARKER_RE = re.compile(r'^url\(\s*[\"\']?#([^\)\s\"\']+)[\"\']?\s*\)$')


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def local_name(element):
    return element.tag.rsplit('}', 1)[-1]


def finite_number(value, svg_length=False):
    if isinstance(value, bool) or value is None:
        raise ValueError('Expected a finite number, got %r' % (value,))
    if isinstance(value, str):
        if svg_length:
            match = LENGTH_RE.match(value)
            if not match:
                raise ValueError('Expected a unitless or px SVG length, got %r' % value)
            value = match.group(1)
        value = float(value.strip())
    else:
        value = float(value)
    if not math.isfinite(value):
        raise ValueError('Non-finite number: %r' % value)
    return value


def spec_rectangle(item):
    rect = [finite_number(item[key]) for key in ['x', 'y', 'w', 'h']]
    if rect[2] <= 0 or rect[3] <= 0:
        raise ValueError('Rectangle width and height must be positive')
    return rect


def reject_transforms(element, parents):
    current = element
    while current is not None:
        if current.get('transform'):
            raise ValueError('Transformed geometry is not supported; use viewBox coordinates')
        current = parents.get(current)


def svg_rectangle(element, parents):
    reject_transforms(element, parents)
    rect = [finite_number(element.get(key), svg_length=True)
            for key in ['x', 'y', 'width', 'height']]
    if rect[2] <= 0 or rect[3] <= 0:
        raise ValueError('SVG rectangle width and height must be positive')
    return rect


def boundary(source, target):
    cx, cy = source[0] + source[2] / 2, source[1] + source[3] / 2
    tx, ty = target[0] + target[2] / 2, target[1] + target[3] / 2
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        raise ValueError('Coincident node centers require explicit custom points')

    def intersect(rect, vx, vy):
        cx0, cy0 = rect[0] + rect[2] / 2, rect[1] + rect[3] / 2
        sx = rect[2] / (2 * abs(vx)) if vx else math.inf
        sy = rect[3] / (2 * abs(vy)) if vy else math.inf
        scale = min(sx, sy)
        return [cx0 + vx * scale, cy0 + vy * scale]

    return [intersect(source, dx, dy), intersect(target, -dx, -dy)]


def parse_points(value):
    if not isinstance(value, list) or len(value) < 2:
        raise ValueError('Connector points must be a list containing at least two points')
    points = []
    for point in value:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError('Each connector point must contain exactly x and y')
        points.append([finite_number(point[0]), finite_number(point[1])])
    return points


def distance_to_segment(point, start, end):
    px, py = point
    ax, ay = start
    bx, by = end
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def distance_to_boundary(point, rect):
    x, y, w, h = rect
    a, b, c, d = [x, y], [x + w, y], [x + w, y + h], [x, y + h]
    return min(distance_to_segment(point, a, b),
               distance_to_segment(point, b, c),
               distance_to_segment(point, c, d),
               distance_to_segment(point, d, a))


def encloses(outer, inner, tolerance):
    return (inner[0] >= outer[0] - tolerance and
            inner[1] >= outer[1] - tolerance and
            inner[0] + inner[2] <= outer[0] + outer[2] + tolerance and
            inner[1] + inner[3] <= outer[1] + outer[3] + tolerance)


def point_lists_equal(actual, expected, tolerance):
    return (len(actual) == len(expected) and
            all(len(a) == len(e) and
                all(abs(av - ev) <= tolerance for av, ev in zip(a, e))
                for a, e in zip(actual, expected)))


def text_value(element):
    children = list(element)
    if children and all(local_name(child) == 'tspan' for child in children):
        surrounding = (element.text or '') + ''.join(child.tail or '' for child in children)
        if not surrounding.strip():
            return '\n'.join(''.join(child.itertext()) for child in children)
    return ''.join(element.itertext())


def marker_fragment(value):
    if value is None or value.strip() in ('', 'none'):
        return None
    match = MARKER_RE.match(value.strip())
    return match.group(1) if match else 'unrecognized:' + value.strip()


def inline_markers(element):
    values = {name: element.get(name) for name in ['marker-start', 'marker-mid', 'marker-end']}
    style = element.get('style', '')
    for declaration in style.split(';'):
        if ':' not in declaration:
            continue
        key, value = declaration.split(':', 1)
        key = key.strip()
        if key in values:
            values[key] = value.strip()
    return values


def svg_polyline_points(element):
    raw = element.get('points', '')
    values = NUMBER_RE.findall(raw)
    residue = NUMBER_RE.sub('', raw)
    if residue.strip(' \t\r\n,'):
        raise ValueError('Unrecognized syntax in polyline points: %r' % raw)
    if len(values) < 4 or len(values) % 2:
        raise ValueError('Polyline needs at least two x/y points')
    numbers = [finite_number(value) for value in values]
    return [[numbers[i], numbers[i + 1]] for i in range(0, len(numbers), 2)]


def connector_geometry(element, parents):
    reject_transforms(element, parents)
    kind = local_name(element)
    if kind == 'polyline':
        return svg_polyline_points(element)
    if kind == 'line':
        return [[finite_number(element.get('x1'), True), finite_number(element.get('y1'), True)],
                [finite_number(element.get('x2'), True), finite_number(element.get('y2'), True)]]
    raise ValueError('Only polyline and line connector geometry is supported')


def perform_audit(spec_path, svg_path, tolerance):
    spec = json.loads(pathlib.Path(spec_path).read_text(encoding='utf-8'))
    if not isinstance(spec, dict):
        raise ValueError('Figure spec must be a JSON object')
    root = ET.parse(svg_path).getroot()
    if local_name(root) != 'svg':
        raise ValueError('SVG document root must be an svg element')
    parents = {child: parent for parent in root.iter() for child in parent}
    checks = []

    def add(check_id, passed, actual, expected, status=None):
        if status is None:
            status = 'passed' if passed else 'failed'
        checks.append({'id': check_id, 'status': status, 'passed': bool(passed),
                       'scope': 'mechanical_spec_svg_consistency',
                       'actual': actual, 'expected': expected})

    def failed(check_id, error, expected):
        add(check_id, False, {'error': str(error)}, expected, status='failed')

    sections = {}
    semantic_entries = []
    for section in ['groups', 'nodes', 'edges']:
        value = spec.get(section, [])
        if not isinstance(value, list):
            raise ValueError('Spec field %s must be a list' % section)
        sections[section] = value
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                raise ValueError('%s[%d] must be an object' % (section, index))
            semantic_entries.append((section, index, item))

    invalid_ids = []
    semantic_ids = []
    for section, index, item in semantic_entries:
        ident = item.get('id')
        if not isinstance(ident, str) or not ident:
            invalid_ids.append({'section': section, 'index': index, 'id': ident})
        else:
            semantic_ids.append(ident)
    duplicates = sorted({ident for ident in semantic_ids if semantic_ids.count(ident) > 1})
    add('spec.semantic_ids.unique', not duplicates and not invalid_ids,
        {'ids': semantic_ids, 'duplicates': duplicates, 'invalid_ids': invalid_ids},
        {'ids': 'non-empty strings unique across groups, nodes, and edges'})

    groups = {item['id']: item for item in sections['groups']
              if isinstance(item.get('id'), str) and item['id']}
    nodes = {item['id']: item for item in sections['nodes']
             if isinstance(item.get('id'), str) and item['id']}

    spec_rects = {}
    for section in ['groups', 'nodes']:
        for item in sections[section]:
            ident = item.get('id')
            check_id = 'spec.rectangle.%s.%s' % (section, ident)
            try:
                rect = spec_rectangle(item)
                if isinstance(ident, str) and ident:
                    spec_rects[(section, ident)] = rect
                add(check_id, True, {'x': item.get('x'), 'y': item.get('y'),
                                     'w': item.get('w'), 'h': item.get('h'),
                                     'normalized': rect},
                    {'finite_numbers': True, 'positive_w_h': True})
            except Exception as exc:
                failed(check_id, exc, {'finite_numbers': True, 'positive_w_h': True})

    xml_index = {}
    xml_id_occurrences = []
    for element in root.iter():
        ident = element.get('id')
        if ident is not None:
            xml_index.setdefault(ident, []).append(element)
            xml_id_occurrences.append(ident)
    xml_duplicates = sorted({ident for ident in xml_id_occurrences
                             if xml_id_occurrences.count(ident) > 1})
    add('svg.xml_ids.unique', not xml_duplicates,
        {'id_count': len(xml_id_occurrences), 'duplicates': xml_duplicates},
        {'duplicate_ids': []})

    for section, index, item in semantic_entries:
        ident = item.get('id')
        if not isinstance(ident, str) or not ident:
            continue
        matches = xml_index.get(ident, [])
        add('svg.semantic_id.%s' % ident, len(matches) == 1 and local_name(matches[0]) == 'g',
            {'occurrences': len(matches),
             'tags': [local_name(match) for match in matches]},
            {'occurrences': 1, 'tag': 'g', 'spec_section': section, 'spec_index': index})

    for layer in LAYERS:
        ident = 'layer-' + layer
        matches = xml_index.get(ident, [])
        add('svg.layer.%s' % layer,
            len(matches) == 1 and local_name(matches[0]) == 'g',
            {'id': ident, 'occurrences': len(matches),
             'tags': [local_name(match) for match in matches]},
            {'id': ident, 'occurrences': 1, 'tag': 'g'})

    def direct_rect(ident, node=False):
        matches = xml_index.get(ident, [])
        if len(matches) != 1:
            raise ValueError('Expected exactly one semantic group with id %r' % ident)
        group = matches[0]
        if group.get('transform'):
            raise ValueError('Transformed semantic groups are not supported; use viewBox coordinates')
        candidates = [child for child in list(group) if local_name(child) == 'rect']
        if node:
            shaped = [child for child in candidates if child.get('id') == ident + '-shape']
            candidates = shaped or candidates
        if len(candidates) != 1:
            raise ValueError('Expected exactly one direct rectangle for %r, found %d' %
                             (ident, len(candidates)))
        return svg_rectangle(candidates[0], parents)

    actual_rects = {}
    for section in ['groups', 'nodes']:
        for item in sections[section]:
            ident = item.get('id')
            if not isinstance(ident, str) or not ident:
                continue
            check_id = 'svg.rectangle.%s.%s' % (section, ident)
            try:
                rect = direct_rect(ident, node=(section == 'nodes'))
                actual_rects[(section, ident)] = rect
                add(check_id, True, {'normalized': rect},
                    {'one_direct_rectangle': True, 'finite_positive_viewBox_geometry': True})
            except Exception as exc:
                failed(check_id, exc,
                       {'one_direct_rectangle': True, 'finite_positive_viewBox_geometry': True})

    expected_text = {}
    for section in ['groups', 'nodes']:
        for item in sections[section]:
            if 'label' not in item:
                raise ValueError('%s %r requires a label' % (section, item.get('id')))
            expected_text[item['id'] + '-label'] = str(item['label'])
    for edge in sections['edges']:
        if edge.get('label'):
            expected_text[edge['id'] + '-label'] = str(edge['label'])
    legend = spec.get('legend', [])
    if not isinstance(legend, list):
        raise ValueError('Spec field legend must be a list')
    for index, item in enumerate(legend):
        if not isinstance(item, dict) or 'label' not in item:
            raise ValueError('legend[%d] requires a label' % index)
        expected_text['legend-label-%s' % index] = str(item['label'])
    actual_text = {}
    missing_text_ids = []
    for index, element in enumerate(e for e in root.iter() if local_name(e) == 'text'):
        ident = element.get('id')
        key = ident if ident else '<missing-id-%d>' % index
        if not ident:
            missing_text_ids.append(index)
        actual_text[key] = text_value(element)
    add('svg.text_labels.match_spec', actual_text == expected_text and not missing_text_ids,
        {'labels': actual_text, 'missing_id_text_element_indices': missing_text_ids},
        {'labels': expected_text, 'exact_match': True,
         'multiline_tspans': 'joined with newline for comparison'})

    used_markers = set()
    for edge in sections['edges']:
        ident = edge.get('id')
        check_prefix = 'spec.edge.%s' % ident
        source, target = edge.get('source'), edge.get('target')
        missing = [endpoint for endpoint in [source, target] if endpoint not in nodes]
        self_edge = source == target
        add(check_prefix + '.endpoints', not missing and not self_edge,
            {'source': source, 'target': target,
             'undeclared_endpoints': missing, 'self_edge': self_edge},
            {'source_and_target': 'declared node IDs', 'self_edge': False})

        kind = edge.get('kind')
        add(check_prefix + '.supported_kind', kind in SUPPORTED_KINDS,
            {'kind': kind}, {'kind': sorted(SUPPORTED_KINDS)})

        expected_points = None
        custom = bool(edge.get('points'))
        try:
            if custom:
                expected_points = parse_points(edge.get('points'))
            else:
                expected_points = boundary(spec_rects[('nodes', source)],
                                           spec_rects[('nodes', target)])
            add(check_prefix + '.connector_points', True,
                {'mode': 'custom' if custom else 'default', 'points': expected_points},
                {'at_least_two_finite_points': True})
        except Exception as exc:
            failed(check_prefix + '.connector_points', exc,
                   {'at_least_two_finite_points': True,
                    'default_mode': 'noncoincident declared node rectangles'})

        for side, point, endpoint in [('source', 0, source), ('target', -1, target)]:
            check_id = check_prefix + '.%s_boundary' % side
            try:
                if expected_points is None:
                    raise ValueError('No valid spec connector points')
                p = expected_points[point]
                rect = spec_rects[('nodes', endpoint)]
                distance = distance_to_boundary(p, rect)
                add(check_id, distance <= tolerance,
                    {'point': p, 'rectangle': rect, 'distance_to_boundary': distance},
                    {'point_on_%s_rectangle_boundary' % side: True,
                     'maximum_distance': tolerance})
            except Exception as exc:
                failed(check_id, exc,
                       {'point_on_%s_rectangle_boundary' % side: True,
                        'maximum_distance': tolerance})

        matches = xml_index.get(ident, []) if isinstance(ident, str) else []
        connectors = []
        if len(matches) == 1:
            connectors = [element for element in matches[0].iter()
                          if local_name(element) in ['polyline', 'line']]
        actual_points = None
        try:
            if len(connectors) != 1:
                raise ValueError('Expected exactly one polyline/line connector, found %d' %
                                 len(connectors))
            actual_points = connector_geometry(connectors[0], parents)
            add('svg.edge.%s.connector' % ident, True,
                {'tag': local_name(connectors[0]), 'points': actual_points},
                {'one_supported_connector': True})
        except Exception as exc:
            failed('svg.edge.%s.connector' % ident, exc,
                   {'one_supported_connector': True})

        if expected_points is not None:
            add('svg.edge.%s.points_match_spec' % ident,
                actual_points is not None and point_lists_equal(actual_points, expected_points, tolerance),
                {'points': actual_points}, {'points': expected_points, 'tolerance': tolerance})
        else:
            add('svg.edge.%s.points_match_spec' % ident, False,
                {'points': actual_points}, {'valid_spec_connector_points': True})

        for side, point, endpoint in [('source', 0, source), ('target', -1, target)]:
            check_id = 'svg.edge.%s.%s_boundary' % (ident, side)
            try:
                if actual_points is None:
                    raise ValueError('No valid SVG connector points')
                p = actual_points[point]
                rect = actual_rects[('nodes', endpoint)]
                distance = distance_to_boundary(p, rect)
                add(check_id, distance <= tolerance,
                    {'point': p, 'rectangle': rect, 'distance_to_boundary': distance,
                     'coordinate_reference': 'actual SVG rectangle'},
                    {'point_on_%s_rectangle_boundary' % side: True,
                     'maximum_distance': tolerance})
            except Exception as exc:
                failed(check_id, exc,
                       {'point_on_%s_rectangle_boundary' % side: True,
                        'maximum_distance': tolerance})

        marker_values = inline_markers(connectors[0]) if len(connectors) == 1 else {
            'marker-start': None, 'marker-mid': None, 'marker-end': None}
        parsed = {name: marker_fragment(value) for name, value in marker_values.items()}
        if kind in DIRECTED_KINDS:
            expected_marker = 'marker-arrow'
            passed = parsed['marker-end'] == expected_marker
        elif kind == 'inhibition':
            expected_marker = 'marker-inhibition'
            passed = parsed['marker-end'] == expected_marker
        elif kind == 'association':
            expected_marker = None
            passed = all(value is None for value in parsed.values())
        else:
            expected_marker = None
            passed = False
        if expected_marker:
            used_markers.add(expected_marker)
        add('svg.edge.%s.marker_semantics' % ident, passed,
            {'kind': kind, 'attributes': marker_values, 'parsed_markers': parsed},
            {'target_side_marker': expected_marker if kind != 'association' else None,
             'association_all_marker_attributes_absent_or_none': kind == 'association',
             'scientific_relation_validation': 'not_performed_by_helper'})

    for marker in sorted(used_markers):
        matches = xml_index.get(marker, [])
        add('svg.marker_definition.%s' % marker,
            len(matches) == 1 and local_name(matches[0]) == 'marker',
            {'occurrences': len(matches), 'tags': [local_name(match) for match in matches]},
            {'id': marker, 'occurrences': 1, 'tag': 'marker'})

    for node in sections['nodes']:
        node_id = node.get('id')
        for field in ['group', 'compartment', 'parent']:
            if field not in node or node.get(field) is None:
                continue
            container = node.get(field)
            base = 'membership.%s.%s' % (node_id, field)
            declared = container in groups
            spec_enclosed = False
            actual = {'container': container, 'declared_group': declared}
            try:
                node_rect = spec_rects[('nodes', node_id)]
                container_rect = spec_rects[('groups', container)]
                spec_enclosed = encloses(container_rect, node_rect, tolerance)
                actual.update({'spec_node_rectangle': node_rect,
                               'spec_container_rectangle': container_rect,
                               'spec_encloses': spec_enclosed})
            except Exception as exc:
                actual['spec_error'] = str(exc)
            add('spec.' + base, declared and spec_enclosed, actual,
                {'declared_group': True, 'container_encloses_node_rectangle': True,
                 'tolerance': tolerance})

            svg_enclosed = False
            actual = {'container': container, 'declared_group': declared}
            try:
                node_rect = actual_rects[('nodes', node_id)]
                container_rect = actual_rects[('groups', container)]
                svg_enclosed = encloses(container_rect, node_rect, tolerance)
                actual.update({'svg_node_rectangle': node_rect,
                               'svg_container_rectangle': container_rect,
                               'svg_encloses': svg_enclosed})
            except Exception as exc:
                actual['svg_error'] = str(exc)
            add('svg.' + base, declared and svg_enclosed, actual,
                {'declared_group': True, 'container_encloses_node_rectangle': True,
                 'tolerance': tolerance})

    return checks


def write_report(path, report):
    destination = pathlib.Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + '.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True, help='Authored figure_spec.json')
    parser.add_argument('--svg', required=True, help='Actually rendered SVG to inspect')
    parser.add_argument('--out', required=True, help='JSON report; always written after processing starts')
    parser.add_argument('--tolerance', type=float, default=0.01,
                        help='Geometry tolerance in SVG/spec user units (default: 0.01)')
    args = parser.parse_args()
    report = {
        'tool': 'structure_audit.py',
        'version': VERSION,
        'spec': args.spec,
        'svg': args.svg,
        'tolerance': args.tolerance,
        'status': 'error',
        'passed': False,
        'scope': {
            'performed': 'Mechanical authored-spec/SVG ID, text, marker, endpoint, and enclosure checks',
            'scientific_validation': 'not_performed_by_helper',
            'edge_direction_from_actual_source': 'not_performed_by_helper',
            'visual_collision_review': 'not_performed_by_helper',
            'human_review': 'not_performed_by_helper',
            'geometry_limit': 'Unitless/px viewBox geometry; transformed/path connectors require explicit conversion or separate review'
        },
        'checks': []
    }
    caught = None
    try:
        if not math.isfinite(args.tolerance) or args.tolerance < 0:
            raise ValueError('Tolerance must be a finite nonnegative number')
        report['spec_sha256'] = sha256(args.spec)
        report['svg_sha256'] = sha256(args.svg)
        report['checks'] = perform_audit(args.spec, args.svg, args.tolerance)
        failures = [check for check in report['checks'] if not check['passed']]
        report['passed'] = not failures
        report['status'] = 'passed' if not failures else 'failed'
        report['summary'] = {
            'total': len(report['checks']),
            'passed': sum(1 for check in report['checks'] if check['passed']),
            'failed': len(failures),
            'failed_check_ids': [check['id'] for check in failures]
        }
    except Exception as exc:
        caught = exc
        report['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        report['checks'].append({
            'id': 'input.processing', 'status': 'error', 'passed': False,
            'scope': 'mechanical_input_processing',
            'actual': {'error': str(exc)},
            'expected': {'readable_json_spec': True, 'parseable_svg': True,
                         'complete_audit_without_processing_error': True}
        })
        report['summary'] = {'total': 1, 'passed': 0, 'failed': 1,
                             'failed_check_ids': ['input.processing']}
    finally:
        write_report(args.out, report)
    print(json.dumps({'status': report['status'], 'output': args.out,
                      'failed_checks': report['summary']['failed']}, ensure_ascii=False))
    if caught is not None:
        print('%s: %s' % (type(caught).__name__, caught), file=sys.stderr)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    sys.exit(main())
