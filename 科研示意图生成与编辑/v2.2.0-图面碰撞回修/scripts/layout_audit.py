#!/usr/bin/env python3
"""Deterministic, approximate SVG layout audit using only Python's stdlib.

This tool finds mechanical layout risks; it does not use font shaping or replace
rendered visual inspection, and it never assesses scientific correctness.
"""
import argparse
import hashlib
import json
import math
import os
import pathlib
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET

VERSION = "2.2.0"
SVG = "http://www.w3.org/2000/svg"
XML = "http://www.w3.org/XML/1998/namespace"
NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
NUMBER_RE = re.compile(NUMBER)
TRANSFORM_RE = re.compile(r"([A-Za-z]+)\s*\(([^)]*)\)")
RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
INHERITED = {
    "fill", "stroke", "stroke-width", "font-family", "font-size",
    "font-style", "font-weight", "text-anchor", "visibility",
}
SKIP_SUBTREES = {"defs", "marker", "symbol", "clipPath", "mask", "pattern", "metadata"}
SHAPES = {"rect", "circle", "ellipse", "image"}


def local_name(element):
    return element.tag.rsplit("}", 1)[-1] if isinstance(element.tag, str) else ""


def finite(value):
    return math.isfinite(value)


def clean_number(value):
    value = float(value)
    if not finite(value):
        raise ValueError("Non-finite SVG number")
    return value


def numbers(value):
    return [clean_number(x) for x in re.findall(NUMBER, value or "")]


def length(value, default=0.0, relative=None):
    if value is None or not str(value).strip():
        return float(default)
    match = re.fullmatch(r"\s*(%s)\s*([A-Za-z%%]*)\s*" % NUMBER, str(value))
    if not match:
        raise ValueError("Unsupported SVG length: %s" % value)
    result = clean_number(match.group(1))
    unit = match.group(2).lower()
    factors = {"": 1.0, "px": 1.0, "pt": 96.0 / 72.0,
               "pc": 16.0, "mm": 96.0 / 25.4, "cm": 96.0 / 2.54,
               "in": 96.0}
    if unit == "%":
        if relative is None:
            raise ValueError("Percentage length has no resolved reference: %s" % value)
        return result * relative / 100.0
    if unit == "em":
        if relative is None:
            raise ValueError("em length has no resolved font size: %s" % value)
        return result * relative
    if unit not in factors:
        raise ValueError("Unsupported SVG length unit: %s" % value)
    return result * factors[unit]


def parse_declarations(value):
    result = {}
    for declaration in (value or "").split(";"):
        if ":" in declaration:
            key, val = declaration.split(":", 1)
            result[key.strip().lower()] = val.strip()
    return result


def parse_stylesheet(root):
    rules = []
    custom_fonts = []
    for style in root.iter():
        if local_name(style) != "style":
            continue
        css = "".join(style.itertext())
        if re.search(r"@font-face\b", css, re.I):
            custom_fonts.append(style)
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        # @font-face blocks are deliberately not treated as element style rules.
        css = re.sub(r"@font-face\b[^{}]*\{[^{}]*\}", "", css, flags=re.I | re.S)
        for selectors, declarations in RULE_RE.findall(css):
            if selectors.strip().startswith("@"):
                continue
            parsed = parse_declarations(declarations)
            for selector in selectors.split(","):
                match = re.fullmatch(
                    r"\s*(?:(\*|[A-Za-z_][\w:.-]*)?)(?:\.([\w-]+)|#([\w-]+))?\s*",
                    selector)
                if match and (match.group(1) or match.group(2) or match.group(3)):
                    rules.append((match.groups(), parsed))
                elif selector.strip():
                    # Complex selectors are ignored rather than matched incorrectly.
                    rules.append((None, parsed))
    return rules, custom_fonts


def selector_matches(element, selector):
    tag, class_name, ident = selector
    if tag and tag != "*" and tag != local_name(element):
        return False
    if class_name and class_name not in (element.get("class") or "").split():
        return False
    if ident and ident != element.get("id"):
        return False
    return True


def computed_style(element, parent, rules):
    style = {key: parent[key] for key in INHERITED if key in parent}
    for key in INHERITED | {"display", "opacity"}:
        if element.get(key) is not None:
            style[key] = element.get(key)
    for selector, declarations in rules:
        if selector is not None and selector_matches(element, selector):
            style.update(declarations)
    style.update(parse_declarations(element.get("style")))
    return style


def multiply(left, right):
    a, b, c, d, e, f = left
    g, h, i, j, k, l = right
    return (a*g + c*h, b*g + d*h, a*i + c*j, b*i + d*j,
            a*k + c*l + e, b*k + d*l + f)


def translation(x, y):
    return (1.0, 0.0, 0.0, 1.0, x, y)


def parse_transform(value):
    """Return affine matrix, contains_rotation_or_skew, unsupported descriptions."""
    if not value or not value.strip():
        return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), False, []
    matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    rotated = False
    unsupported = []
    position = 0
    for match in TRANSFORM_RE.finditer(value):
        if value[position:match.start()].strip(" ,\t\r\n"):
            unsupported.append("Unparsed transform syntax")
        position = match.end()
        name = match.group(1)
        args = numbers(match.group(2))
        current = None
        try:
            if name == "translate" and len(args) in (1, 2):
                current = translation(args[0], args[1] if len(args) == 2 else 0.0)
            elif name == "scale" and len(args) in (1, 2):
                current = (args[0], 0.0, 0.0, args[-1], 0.0, 0.0)
            elif name == "matrix" and len(args) == 6:
                current = tuple(args)
            elif name == "rotate" and len(args) in (1, 3):
                rotated = True
                angle = math.radians(args[0])
                cosine, sine = math.cos(angle), math.sin(angle)
                rotation = (cosine, sine, -sine, cosine, 0.0, 0.0)
                current = rotation
                if len(args) == 3:
                    current = multiply(multiply(translation(args[1], args[2]), rotation),
                                       translation(-args[1], -args[2]))
            elif name in ("skewX", "skewY") and len(args) == 1:
                rotated = True
                tangent = math.tan(math.radians(args[0]))
                current = ((1.0, 0.0, tangent, 1.0, 0.0, 0.0) if name == "skewX"
                           else (1.0, tangent, 0.0, 1.0, 0.0, 0.0))
            else:
                unsupported.append("Unsupported transform: %s" % name)
        except (ValueError, OverflowError, ZeroDivisionError) as exc:
            unsupported.append("Invalid transform %s: %s" % (name, exc))
        if current is not None:
            matrix = multiply(matrix, current)
    if position < len(value) and value[position:].strip(" ,\t\r\n"):
        unsupported.append("Unparsed transform suffix")
    if not all(finite(x) for x in matrix):
        raise ValueError("Non-finite transform matrix")
    return matrix, rotated, unsupported


def point(matrix, x, y):
    a, b, c, d, e, f = matrix
    return a*x + c*y + e, b*x + d*y + f


def make_box(x, y, width, height):
    return (x, y, x + width, y + height)


def normalized_box(box):
    return (min(box[0], box[2]), min(box[1], box[3]),
            max(box[0], box[2]), max(box[1], box[3]))


def union(boxes):
    boxes = list(boxes)
    if not boxes:
        return None
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def transform_box(box, matrix):
    x1, y1, x2, y2 = box
    points = [point(matrix, x, y) for x, y in
              ((x1, y1), (x1, y2), (x2, y1), (x2, y2))]
    return (min(p[0] for p in points), min(p[1] for p in points),
            max(p[0] for p in points), max(p[1] for p in points))


def box_json(box):
    if box is None:
        return None
    rounded = [round(float(x), 4) for x in normalized_box(box)]
    return {"x": rounded[0], "y": rounded[1],
            "x2": rounded[2], "y2": rounded[3],
            "width": round(rounded[2] - rounded[0], 4),
            "height": round(rounded[3] - rounded[1], 4)}


def intersection(left, right):
    box = (max(left[0], right[0]), max(left[1], right[1]),
           min(left[2], right[2]), min(left[3], right[3]))
    if box[2] - box[0] <= 0.01 or box[3] - box[1] <= 0.01:
        return None
    return box


def expand(box, amount):
    return (box[0] - amount, box[1] - amount, box[2] + amount, box[3] + amount)


def segment_hits_box(start, end, box):
    """Liang-Barsky segment/AABB test, including an edge touch."""
    x, y = start
    dx, dy = end[0] - x, end[1] - y
    low, high = 0.0, 1.0
    for p, q in ((-dx, x-box[0]), (dx, box[2]-x),
                 (-dy, y-box[1]), (dy, box[3]-y)):
        if abs(p) < 1e-12:
            if q < 0:
                return False
        else:
            ratio = q / p
            if p < 0:
                low = max(low, ratio)
            else:
                high = min(high, ratio)
            if low > high:
                return False
    return True


def glyph_em_width(char):
    category = unicodedata.category(char)
    if category in ("Mn", "Me", "Cf"):
        return 0.0
    if char == "\t":
        return 4.0 * 0.333
    if char.isspace():
        return 0.333
    if unicodedata.east_asian_width(char) in ("W", "F"):
        return 1.0
    if char in "ilI.,'`|!:;":
        return 0.30
    if char in "mwMW@":
        return 0.85
    if char.isupper():
        return 0.65
    if char.islower() or char.isdigit():
        return 0.56
    if unicodedata.category(char).startswith("P"):
        return 0.36
    return 0.60


def text_width(value, font_size):
    return sum(glyph_em_width(char) for char in value) * font_size


def whitespace(value, preserve=False):
    value = value or ""
    return value if preserve else re.sub(r"\s+", " ", value)


def text_layout(element, matrix, style, rules, matrix_rotated, add_review):
    """Approximate text/tspan chunks, returning global boxes and review flags."""
    initial_size = length(style.get("font-size", "16"), 16)
    state = {"x": length(element.get("x"), 0),
             "y": length(element.get("y"), 0)}
    lines = []

    def visit(node, parent_matrix, parent_style, cursor, is_root=False):
        nonlocal lines
        node_style = parent_style if is_root else computed_style(node, parent_style, rules)
        if node_style.get("display") == "none" or node_style.get("visibility") in ("hidden", "collapse"):
            return cursor
        node_matrix, rotated, unsupported = parse_transform(node.get("transform"))
        node_matrix = multiply(parent_matrix, node_matrix) if not is_root else parent_matrix
        rotated = rotated or matrix_rotated
        if not is_root:
            for reason in unsupported:
                add_review(node, "unsupported_text_transform", reason)
        if rotated and not is_root:
            add_review(node, "rotated_text", "Rotated/skewed text uses an estimated affine box")
        if node.get("rotate") is not None:
            add_review(node, "rotated_text", "The SVG rotate glyph attribute is not font-exact")
        if node.get("textLength") is not None:
            add_review(node, "unsupported_text_layout", "textLength/lengthAdjust is not modeled")
        if node.get("baseline-shift") is not None:
            add_review(node, "unsupported_text_layout", "baseline-shift is not modeled")
        try:
            size = length(node_style.get("font-size", "16"), initial_size,
                          relative=initial_size)
        except ValueError as exc:
            add_review(node, "unsupported_font_size", str(exc))
            size = initial_size
        x = cursor[0]
        y = cursor[1]
        try:
            if node.get("x") is not None:
                x = length(node.get("x"), x)
            if node.get("y") is not None:
                y = length(node.get("y"), y)
            x += length(node.get("dx"), 0)
            y += length(node.get("dy"), 0)
        except ValueError as exc:
            add_review(node, "unsupported_text_position", str(exc))
        preserve = node.get("{%s}space" % XML) == "preserve"
        own_x_or_y = node.get("x") is not None or node.get("y") is not None
        anchor = node_style.get("text-anchor", "start")
        if anchor not in ("start", "middle", "end"):
            add_review(node, "unsupported_text_anchor", str(anchor))
            anchor = "start"

        def emit(content, at_new_position):
            nonlocal x, y
            content = whitespace(content, preserve)
            if not content.strip():
                # Collapsed separating spaces do not establish a separate chunk.
                return
            width = text_width(content, size)
            start_x = x
            if is_root or own_x_or_y or at_new_position:
                if anchor == "middle":
                    start_x -= width / 2.0
                elif anchor == "end":
                    start_x -= width
            local = (start_x, y - size * 0.8, start_x + width, y + size * 0.2)
            global_box = transform_box(local, node_matrix)
            start = point(node_matrix, start_x, y)
            end = point(node_matrix, start_x + width, y)
            lines.append({"text": content, "estimated_bbox": global_box,
                          "estimated_baseline": (start, end), "font_size": size})
            x += width

        emit(node.text, False)
        for child in node:
            if local_name(child) == "textPath":
                add_review(child, "path_text", "textPath geometry is not modeled")
            if local_name(child) in ("tspan", "textPath"):
                cursor = visit(child, node_matrix, node_style, (x, y))
                x, y = cursor
            elif list(child.itertext()):
                add_review(child, "unsupported_text_child",
                           "Unsupported <%s> inside text" % local_name(child))
            emit(child.tail, False)
        return x, y

    visit(element, matrix, style, (state["x"], state["y"]), True)
    return lines


def path_segments(d):
    """Return sampled open/closed path segments and unsupported command names."""
    tokens = re.findall(r"[AaCcHhLlMmQqSsTtVvZz]|%s" % NUMBER, d or "")
    residue = re.sub(r"[AaCcHhLlMmQqSsTtVvZz]|%s|[\s,]+" % NUMBER, "", d or "")
    if residue:
        raise ValueError("Unparsed path data near: %s" % residue[:30])
    index = 0
    command = None
    current = (0.0, 0.0)
    start = current
    previous_cubic = None
    previous_quad = None
    segments = []
    unsupported = []

    def take(count):
        nonlocal index
        if index + count > len(tokens) or any(t.isalpha() for t in tokens[index:index+count]):
            raise ValueError("Incomplete %s path command" % command)
        values = [clean_number(t) for t in tokens[index:index+count]]
        index += count
        return values

    def absolute(x, y, relative):
        return (current[0] + x, current[1] + y) if relative else (x, y)

    while index < len(tokens):
        if tokens[index].isalpha():
            command = tokens[index]
            index += 1
        elif command is None:
            raise ValueError("Path does not start with a command")
        if command in ("Z", "z"):
            if current != start:
                segments.append((current, start))
            current = start
            previous_cubic = previous_quad = None
            command = None
            continue
        relative = command.islower()
        op = command.upper()
        if op == "M":
            x, y = take(2)
            current = absolute(x, y, relative)
            start = current
            command = "l" if relative else "L"
        elif op == "L":
            x, y = take(2)
            endpoint = absolute(x, y, relative)
            segments.append((current, endpoint))
            current = endpoint
        elif op == "H":
            x = take(1)[0]
            endpoint = (current[0] + x if relative else x, current[1])
            segments.append((current, endpoint))
            current = endpoint
        elif op == "V":
            y = take(1)[0]
            endpoint = (current[0], current[1] + y if relative else y)
            segments.append((current, endpoint))
            current = endpoint
        elif op in ("C", "S"):
            values = take(6 if op == "C" else 4)
            if op == "C":
                c1 = absolute(values[0], values[1], relative)
                c2 = absolute(values[2], values[3], relative)
                endpoint = absolute(values[4], values[5], relative)
            else:
                c1 = ((2*current[0]-previous_cubic[0], 2*current[1]-previous_cubic[1])
                      if previous_cubic else current)
                c2 = absolute(values[0], values[1], relative)
                endpoint = absolute(values[2], values[3], relative)
            origin = current
            for step in range(1, 17):
                t = step / 16.0
                u = 1.0 - t
                sampled = (u**3*origin[0] + 3*u*u*t*c1[0] + 3*u*t*t*c2[0] + t**3*endpoint[0],
                           u**3*origin[1] + 3*u*u*t*c1[1] + 3*u*t*t*c2[1] + t**3*endpoint[1])
                segments.append((current, sampled))
                current = sampled
            previous_cubic = c2
            previous_quad = None
            continue
        elif op in ("Q", "T"):
            values = take(4 if op == "Q" else 2)
            if op == "Q":
                control = absolute(values[0], values[1], relative)
                endpoint = absolute(values[2], values[3], relative)
            else:
                control = ((2*current[0]-previous_quad[0], 2*current[1]-previous_quad[1])
                           if previous_quad else current)
                endpoint = absolute(values[0], values[1], relative)
            origin = current
            for step in range(1, 17):
                t = step / 16.0
                u = 1.0 - t
                sampled = (u*u*origin[0] + 2*u*t*control[0] + t*t*endpoint[0],
                           u*u*origin[1] + 2*u*t*control[1] + t*t*endpoint[1])
                segments.append((current, sampled))
                current = sampled
            previous_quad = control
            previous_cubic = None
            continue
        elif op == "A":
            values = take(7)
            endpoint = absolute(values[5], values[6], relative)
            # A straight fallback is explicitly disclosed; no claim of arc accuracy.
            segments.append((current, endpoint))
            current = endpoint
            unsupported.append("A")
        else:
            raise ValueError("Unsupported path command: %s" % command)
        if op not in ("C", "S"):
            previous_cubic = None
        if op not in ("Q", "T"):
            previous_quad = None
    return segments, unsupported


def audit_svg(root, source_bytes):
    texts = []
    connectors = []
    geometries = []
    reviews = []
    review_keys = set()
    counters = {}
    references = {}
    ids_seen = {}
    rules, custom_fonts = parse_stylesheet(root)

    def reference(element):
        if element in references:
            return references[element]
        tag = local_name(element)
        counters[tag] = counters.get(tag, 0) + 1
        ident = element.get("id")
        if ident:
            if ident in ids_seen:
                add_review(element, "duplicate_id", "Duplicate IDs make element references ambiguous")
            ids_seen[ident] = element
            ref = ident
        else:
            ref = "%s[%d](no-id)" % (tag, counters[tag])
        references[element] = ref
        return ref

    def add_review(element, kind, reason):
        ref = reference(element)
        key = (ref, kind, reason)
        if key not in review_keys:
            review_keys.add(key)
            reviews.append({"element_ids": [ref], "type": kind,
                            "reason": reason, "severity": "needs_visual_review",
                            "scope": "element_or_descendants"})

    for element in custom_fonts:
        add_review(element, "unsupported_custom_font",
                   "@font-face/custom font resolution and actual glyph metrics are unavailable")
    for element in root.iter():
        if local_name(element) in ("font", "font-face", "font-face-uri"):
            add_review(element, "unsupported_custom_font",
                       "SVG font glyph metrics are unavailable; deterministic estimates only")

    def style_size(style):
        return length(style.get("font-size", "16"), 16)

    def stroke_width(style):
        try:
            return max(0.0, length(style.get("stroke-width", "1"), 1))
        except ValueError:
            return 1.0

    def record_geometry(element, box, matrix, style, kind):
        margin = stroke_width(style) / 2.0 if style.get("stroke", "none") != "none" else 0.0
        box = expand(box, margin)
        geometries.append({"ref": reference(element), "tag": local_name(element),
                           "bbox": transform_box(box, matrix), "kind": kind})

    def walk(element, matrix, parent_style, rotated_context=False, parent_hidden=False):
        tag = local_name(element)
        if tag in SKIP_SUBTREES:
            return
        style = computed_style(element, parent_style, rules)
        hidden = parent_hidden or style.get("display") == "none" or style.get("visibility") in ("hidden", "collapse")
        try:
            if float(style.get("opacity", "1")) == 0:
                hidden = True
        except ValueError:
            add_review(element, "unsupported_opacity", "Opacity is not numeric")
        local_matrix, rotated, unsupported = parse_transform(element.get("transform"))
        matrix = multiply(matrix, local_matrix)
        rotated_context = rotated_context or rotated
        if style.get("transform"):
            add_review(element, "unsupported_css_transform", "CSS transform property is not applied")
        for reason in unsupported:
            add_review(element, "unsupported_transform", reason)
        if tag == "svg" and element is not root:
            add_review(element, "nested_svg", "Nested SVG viewport/viewBox mapping is not modeled")
        if hidden:
            return
        if tag == "text":
            if rotated_context:
                add_review(element, "rotated_text", "Rotated/skewed text uses an estimated affine box")
            try:
                lines = text_layout(element, matrix, style, rules, rotated_context, add_review)
                box = union(line["estimated_bbox"] for line in lines)
                if box is not None:
                    texts.append({"ref": reference(element), "tag": tag,
                                  "text": "".join(element.itertext()),
                                  "font_family": style.get("font-family", "unspecified"),
                                  "font_size": style_size(style), "bbox": box, "lines": lines})
            except (ValueError, OverflowError) as exc:
                add_review(element, "unsupported_text", "Text not geometrically audited: %s" % exc)
        try:
            if tag == "line" and style.get("stroke", "none") != "none":
                p1 = point(matrix, length(element.get("x1"), 0), length(element.get("y1"), 0))
                p2 = point(matrix, length(element.get("x2"), 0), length(element.get("y2"), 0))
                connectors.append({"ref": reference(element), "segments": [(p1, p2)],
                                   "stroke_width": stroke_width(style)})
                record_geometry(element, (min(p1[0], p2[0]), min(p1[1], p2[1]),
                                          max(p1[0], p2[0]), max(p1[1], p2[1])),
                                (1, 0, 0, 1, 0, 0), style, "measured_line_geometry")
            elif tag in ("polyline", "polygon") and style.get("stroke", "none") != "none":
                pts = numbers(element.get("points"))
                if len(pts) < 4 or len(pts) % 2:
                    raise ValueError("Invalid %s points" % tag)
                local_points = list(zip(pts[::2], pts[1::2]))
                pts_global = [point(matrix, x, y) for x, y in local_points]
                if tag == "polygon":
                    pts_global.append(pts_global[0])
                connectors.append({"ref": reference(element),
                                   "segments": list(zip(pts_global, pts_global[1:])),
                                   "stroke_width": stroke_width(style)})
                record_geometry(element, (min(pts[::2]), min(pts[1::2]),
                                          max(pts[::2]), max(pts[1::2])), matrix, style,
                                "measured_polyline_geometry")
            elif tag == "path" and style.get("stroke", "none") != "none":
                segments, unsupported_path = path_segments(element.get("d"))
                for command in unsupported_path:
                    add_review(element, "unsupported_path_arc",
                               "Arc %s approximated by a straight segment" % command)
                global_segments = [(point(matrix, *p1), point(matrix, *p2))
                                   for p1, p2 in segments]
                if global_segments:
                    connectors.append({"ref": reference(element), "segments": global_segments,
                                       "stroke_width": stroke_width(style)})
                    coords = [p for segment in global_segments for p in segment]
                    box = (min(p[0] for p in coords), min(p[1] for p in coords),
                           max(p[0] for p in coords), max(p[1] for p in coords))
                    margin = stroke_width(style) / 2.0
                    geometries.append({"ref": reference(element), "tag": tag,
                                       "bbox": expand(box, margin),
                                       "kind": "sampled_path_geometry"})
            elif tag == "rect" or tag == "image":
                box = make_box(length(element.get("x"), 0), length(element.get("y"), 0),
                               length(element.get("width"), 0), length(element.get("height"), 0))
                visible_paint = tag == "image" or style.get("fill", "black") != "none" or style.get("stroke", "none") != "none"
                if visible_paint and box[2] >= box[0] and box[3] >= box[1]:
                    record_geometry(element, box, matrix, style, "measured_basic_shape")
            elif tag == "circle":
                cx, cy, radius = (length(element.get("cx"), 0), length(element.get("cy"), 0),
                                  length(element.get("r"), 0))
                if radius >= 0 and (style.get("fill", "black") != "none" or style.get("stroke", "none") != "none"):
                    record_geometry(element, make_box(cx-radius, cy-radius, 2*radius, 2*radius),
                                    matrix, style, "measured_basic_shape")
            elif tag == "ellipse":
                cx, cy = length(element.get("cx"), 0), length(element.get("cy"), 0)
                rx, ry = length(element.get("rx"), 0), length(element.get("ry"), 0)
                if rx >= 0 and ry >= 0 and (style.get("fill", "black") != "none" or style.get("stroke", "none") != "none"):
                    record_geometry(element, make_box(cx-rx, cy-ry, 2*rx, 2*ry),
                                    matrix, style, "measured_basic_shape")
            elif tag in ("use", "foreignObject"):
                add_review(element, "unsupported_element", "<%s> geometry is not modeled" % tag)
        except (ValueError, OverflowError) as exc:
            add_review(element, "unsupported_geometry", str(exc))
        for child in element:
            walk(child, matrix, style, rotated_context, hidden)

    defaults = {"font-size": "16", "font-family": "unspecified", "fill": "black",
                "stroke": "none", "stroke-width": "1", "text-anchor": "start",
                "visibility": "visible", "display": "inline", "opacity": "1"}
    walk(root, (1, 0, 0, 1, 0, 0), defaults)

    canvas = None
    view_box = root.get("viewBox")
    if view_box:
        try:
            values = numbers(view_box)
            if len(values) != 4 or values[2] <= 0 or values[3] <= 0:
                raise ValueError("viewBox needs four numbers and positive width/height")
            canvas = (values[0], values[1], values[0]+values[2], values[1]+values[3])
        except ValueError as exc:
            add_review(root, "unsupported_viewBox", str(exc))
    else:
        try:
            width, height = length(root.get("width")), length(root.get("height"))
            if width <= 0 or height <= 0:
                raise ValueError("Canvas width/height are not positive")
            canvas = (0.0, 0.0, width, height)
            add_review(root, "missing_viewBox", "Canvas derived from numeric width/height; no viewBox")
        except ValueError:
            add_review(root, "unknown_canvas", "No usable viewBox or numeric width/height; overflow not checked")

    findings = []

    def add_finding(kind, members, severity, scope, details, overlap=None, segment=None):
        boxes = []
        for member, box, box_kind in members:
            boxes.append({"element_id": member, "kind": box_kind,
                          "estimated_or_derived_bbox": box_json(box)})
        finding = {"id": "L%04d" % (len(findings)+1), "type": kind,
                   "element_ids": [member[0] for member in members],
                   "severity": severity, "scope": scope, "boxes": boxes,
                   "details": details}
        if overlap is not None:
            finding["estimated_intersection_bbox"] = box_json(overlap)
        if segment is not None:
            finding["connector_segment"] = {
                "start": [round(segment[0][0], 4), round(segment[0][1], 4)],
                "end": [round(segment[1][0], 4), round(segment[1][1], 4)]}
        findings.append(finding)

    for text in texts:
        if canvas is not None:
            x1, y1, x2, y2 = canvas
            box = text["bbox"]
            if box[0] < x1-0.01 or box[1] < y1-0.01 or box[2] > x2+0.01 or box[3] > y2+0.01:
                add_finding("canvas_text_overflow",
                            [(text["ref"], box, "estimated_unicode_text_bbox"),
                             (root.get("id") or "svg[1](root)", canvas, "measured_viewBox")],
                            "error", "canvas", "Estimated text bounds exceed the SVG viewBox/canvas")
    for geometry in geometries:
        if canvas is None:
            continue
        x1, y1, x2, y2 = canvas
        box = geometry["bbox"]
        if box[0] < x1-0.01 or box[1] < y1-0.01 or box[2] > x2+0.01 or box[3] > y2+0.01:
            add_finding("canvas_element_overflow",
                        [(geometry["ref"], box, geometry["kind"]),
                         (root.get("id") or "svg[1](root)", canvas, "measured_viewBox")],
                        "error", "canvas", "Basic transformed geometry exceeds the SVG viewBox/canvas")

    for index, left in enumerate(texts):
        for right in texts[index+1:]:
            overlap = intersection(left["bbox"], right["bbox"])
            if overlap:
                add_finding("text_text_collision",
                            [(left["ref"], left["bbox"], "estimated_unicode_text_bbox"),
                             (right["ref"], right["bbox"], "estimated_unicode_text_bbox")],
                            "error", "two_text_elements", "Estimated text bounding boxes overlap", overlap)

    for connector in connectors:
        coords = [p for segment in connector["segments"] for p in segment]
        if not coords:
            continue
        connector_box = (min(p[0] for p in coords), min(p[1] for p in coords),
                         max(p[0] for p in coords), max(p[1] for p in coords))
        for text in texts:
            # A one-user-unit clearance avoids reporting a merely touching stroke as safe.
            target = expand(text["bbox"], connector["stroke_width"] / 2.0 + 1.0)
            hits = [segment for segment in connector["segments"]
                    if segment_hits_box(segment[0], segment[1], target)]
            if hits:
                add_finding("text_connector_overlap",
                            [(text["ref"], text["bbox"], "estimated_unicode_text_bbox"),
                             (connector["ref"], connector_box, "derived_connector_bbox")],
                            "error", "text_and_connector",
                            "A connector segment intersects the estimated label box plus stroke/1-unit clearance",
                            segment=hits[0])

    text_json = []
    for text in texts:
        text_json.append({"element_id": text["ref"], "text": text["text"],
                          "font_family": text["font_family"], "font_size": round(text["font_size"], 4),
                          "estimated_bbox": box_json(text["bbox"]),
                          "lines": [{"text": line["text"], "font_size": round(line["font_size"], 4),
                                     "estimated_bbox": box_json(line["estimated_bbox"])}
                                    for line in text["lines"]]})
    return {
        "canvas": {"viewBox": view_box, "measured_or_derived_bbox": box_json(canvas)},
        "text_elements": text_json,
        "connector_count": len(connectors),
        "findings": findings,
        "needs_visual_review": reviews,
    }


def base_report(svg):
    return {
        "schema_version": "1.0",
        "tool": "layout_audit.py",
        "tool_version": VERSION,
        "svg": str(svg),
        "status": "not_run",
        "mechanical_issue_count": 0,
        "findings": [],
        "needs_visual_review": [],
        "visual_inspection_required": True,
        "scientific_review": "not_performed; layout results do not certify scientific correctness",
        "metric": {
            "name": "deterministic-unicode-em-v1",
            "font_exact": False,
            "disclosure": "No font files, kerning, ligatures, hinting, bidi shaping, or renderer text measurement are used. All text boxes are deterministic approximations, not font-exact measurements.",
            "rules": [
                "East Asian wide/fullwidth characters: 1.0 em; combining/format characters: 0 em",
                "space: 0.333 em; narrow ilI.,'`|!:;: 0.30 em; mwMW@: 0.85 em",
                "uppercase: 0.65 em; lowercase/digits: 0.56 em; other punctuation: 0.36 em; other glyphs: 0.60 em",
                "baseline box: 0.8 em above through 0.2 em below baseline; inherited font-size default 16 user units",
                "affine-transformed rectangles use the axis-aligned bounds of their four transformed corners",
                "connector checks expand text boxes by half the stroke width plus 1 user unit",
                "cubic/quadratic curves use 16 deterministic samples; arcs fall back to a straight segment and need visual review"
            ]
        },
        "limitations": [
            "A zero exit code means no modeled mechanical collision was found, not visual or scientific approval.",
            "Unsupported geometry/text is listed under needs_visual_review and may hide additional collisions.",
            "Final actual rendered PNG/PDF and source SVG must be visually inspected at target size.",
            "Element IDs are actual SVG id values; no-id fallbacks and the root fallback are generated locators, not added IDs."
        ]
    }


def write_report(path, report):
    destination = pathlib.Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                         encoding="utf-8")
    os.replace(str(temporary), str(destination))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit estimated SVG text/layout collisions; always emits JSON when --out is writable.")
    parser.add_argument("--svg", required=True, help="Input SVG (never modified)")
    parser.add_argument("--out", required=True, help="JSON report path")
    args = parser.parse_args(argv)
    if pathlib.Path(args.svg).resolve() == pathlib.Path(args.out).resolve():
        print("layout_audit.py: --out must differ from --svg; no report written to protect the source", file=sys.stderr)
        return 2
    report = base_report(args.svg)
    exit_code = 0
    try:
        source = pathlib.Path(args.svg).read_bytes()
        report["sha256"] = hashlib.sha256(source).hexdigest()
        root = ET.fromstring(source)
        if local_name(root) != "svg":
            raise ValueError("Root element is not SVG")
        result = audit_svg(root, source)
        report.update(result)
        report["mechanical_issue_count"] = len(report["findings"])
        if report["findings"]:
            report["status"] = "mechanical_issues_found_repair_rerender_required"
            exit_code = 1
        else:
            report["status"] = "no_modeled_mechanical_issues_found_visual_review_still_required"
    except (OSError, ET.ParseError, ValueError, OverflowError) as exc:
        report["status"] = "input_or_audit_error"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        exit_code = 2
    except Exception as exc:  # Always leave a machine-readable failure report.
        report["status"] = "unexpected_audit_error"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        exit_code = 2
    try:
        write_report(args.out, report)
    except OSError as exc:
        print("layout_audit.py: cannot write report: %s" % exc, file=sys.stderr)
        return 2
    if exit_code == 2:
        print("layout_audit.py: %s" % report.get("error", {}), file=sys.stderr)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
