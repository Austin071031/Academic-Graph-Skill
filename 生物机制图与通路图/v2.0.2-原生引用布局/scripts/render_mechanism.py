#!/usr/bin/env python3
"""Graph normalization and measurably non-intersecting orthogonal edge routing.

Required code is stdlib-only. Optional Shapely (import shapely/reqproc) is a
verification accelerator, never a runtime prerequisite or evidence of rendering.
"""
import itertools
import json
import math
import re


def safe_id(value, prefix):
    pid = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "")).strip("-.") or prefix
    return ("n-" + pid) if pid[0].isdigit() else pid


def normalize_graph(graph):
    """Normalize only IR structure; do not invent source loc, values or citations."""
    g = json.loads(json.dumps(graph, ensure_ascii=False))
    log = []
    nodes = g.get("nodes", [])
    if not isinstance(nodes, list):
        raise ValueError("nodes must be an array")
    seen = {}
    clean_nodes = []
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            log.append({"kind": "drop_node", "index": i, "reason": "not an object"})
            continue
        ident = safe_id(node.get("id", "node-%d" % i), "node-%d" % i)
        seen[ident] = seen.get(ident, 0) + 1
        if seen[ident] > 1:
            old = ident
            ident = "%s-%d" % (ident, seen[ident])
            log.append({"kind": "unique_id", "from": old, "to": ident})
        node["id"] = ident
        node["type"] = safe_id(node.get("type", "protein"), "protein")
        compartment = node.get("compartment")
        # Intranuclear receptors are legitimate; the usual surface receptor gets
        # a membrane band even if the input omitted it. Every relocation is logged.
        if node["type"] == "receptor" and compartment not in ("nucleus", "mitochondrion", "er", "golgi"):
            if compartment != "membrane":
                log.append({"kind": "compartment", "node": ident, "from": compartment,
                            "to": "membrane"})
            compartment = "membrane"
        else:
            compartment = compartment or "cytoplasm"
        node["compartment"] = safe_id(compartment, "cytoplasm")
        for key in ("x", "y"):
            # Normalize declared and internal names, never silently discard coordinates.
            if key in node and "_" + key not in node:
                node["_" + key] = node[key]
        clean_nodes.append(node)
    g["nodes"] = clean_nodes
    ids = {n["id"] for n in clean_nodes}
    valid_edges = []
    for i, edge in enumerate(g.get("edges", [])):
        if not isinstance(edge, dict):
            log.append({"kind": "drop_edge", "index": i, "reason": "not an object"})
            continue
        src, dst = edge.get("from"), edge.get("to")
        if src not in ids or dst not in ids:
            log.append({"kind": "drop_dangling_edge", "index": i,
                        "id": edge.get("id"), "from": src, "to": dst})
            continue
        edge = dict(edge)
        edge["id"] = safe_id(edge.get("id", "edge-%d" % i), "edge-%d" % i)
        edge["type"] = safe_id(edge.get("type", "unknown"), "unknown")
        valid_edges.append(edge)
    g["edges"] = valid_edges
    original = {c.get("id"): c for c in g.get("compartments", []) if isinstance(c, dict) and c.get("id")}
    used_order = []
    labels = {"extracellular": "Extracellular", "membrane": "Membrane",
              "cytoplasm": "Cytoplasm", "nucleus": "Nucleus"}
    order_map = {"extracellular": 0, "membrane": 1, "cytoplasm": 2,
                 "cytosol": 2, "mitochondrion": 2.4, "golgi": 2.2,
                 "er": 2.3, "nucleus": 3}
    for node in clean_nodes:
        cid = node["compartment"]
        if cid not in used_order:
            used_order.append(cid)
    comps = []
    for cid in sorted(used_order, key=lambda x: original.get(x, {}).get("order", order_map.get(x, 2.5))):
        c = dict(original.get(cid, {}))
        c["id"] = cid
        c.setdefault("label", labels.get(cid, cid))
        c["order"] = c.get("order", order_map.get(cid, 2.5))
        comps.append(c)
    if not any(c["id"] == "cytoplasm" for c in comps):
        pos = 1 if any(c["id"] == "membrane" for c in comps) else len(comps)
        comps.insert(pos, {"id": "cytoplasm", "label": "Cytoplasm", "order": 2})
    g["compartments"] = comps
    if any(n["compartment"] == "membrane" for n in clean_nodes) and not any(c["id"] == "membrane" for c in comps):
        comps.insert(0 if comps and comps[0]["id"] == "extracellular" else 0,
                     {"id": "membrane", "label": "Membrane", "order": 1})
        comps.sort(key=lambda c: c["order"])
    g["normalization_log"] = log
    if not clean_nodes:
        raise ValueError("no valid nodes after graph normalization")
    return g


def aabb(center_box):
    x, y, w, h = center_box
    return [x - w / 2, y - h / 2, x + w / 2, y + h / 2]


def intersect(a, b, gap=9):
    return not (a[2] + gap <= b[0] or b[2] + gap <= a[0]
                or a[3] + gap <= b[1] or b[3] + gap <= a[1])


def segment_intersect(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    def within(p, q, r):
        return min(p[0], r[0]) - 1e-6 <= q[0] <= max(p[0], r[0]) + 1e-6 and min(p[1], r[1]) - 1e-6 <= q[1] <= max(p[1], r[1]) + 1e-6
    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    if (o1 * o2 < 0) and (o3 * o4 < 0):
        return True
    return any(abs(o) < 1e-6 and within(p, q, r) for o, p, q, r in
               [(o1, a, c, b), (o2, a, d, b), (o3, c, a, d), (o4, c, b, d)])


def self_intersections(points):
    count = 0
    for i, j in itertools.combinations(range(len(points) - 1), 2):
        if j <= i + 1:
            continue
        if segment_intersect(points[i], points[i + 1], points[j], points[j + 1]):
            count += 1
    return count


def cubic_points(a, b, c, d, count=64):
    points = []
    for i in range(count + 1):
        t = i / count
        u = 1 - t
        points.append((u**3 * a[0] + 3 * u*u*t * b[0] + 3 * u*t*t * c[0] + t**3 * d[0],
                       u**3 * a[1] + 3 * u*u*t * b[1] + 3 * u*t*t * c[1] + t**3 * d[1]))
    return points


def segment_box_hit(p, q, box):
    if max(p[0], q[0]) < box[0] or min(p[0], q[0]) > box[2] or max(p[1], q[1]) < box[1] or min(p[1], q[1]) > box[3]:
        return False
    if any(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in (p, q)):
        return True
    corners = [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])]
    return any(segment_intersect(p, q, corners[i], corners[(i + 1) % 4]) for i in range(4))


def path_crossings(points, boxes, source, target):
    return sorted(k for k, box in boxes.items() if k not in (source, target)
                  and any(segment_box_hit(points[i], points[i + 1], box)
                          for i in range(len(points) - 1)))


def route_paths(geom, edges, left=32, right=1208):
    """Return actual path plus verification of node avoidance per edge.

    Relation labels/compartments are retained as source IR. A channel is opened
    only when the straight line crosses a different entity. Selection tries both
    sides of the endpoints rather than forcing a semantic compartment change.
    """
    boxes = {k: aabb(v) for k, v in geom.items()}
    output = {}
    for index, edge in enumerate(edges):
        src, dst = edge["from"], edge["to"]
        if src not in geom or dst not in geom:
            continue
        sx, sy, sw, sh = geom[src]
        tx, ty, tw, th = geom[dst]
        a, b = (sx, sy + sh / 2), (tx, ty - th / 2)
        obstacles = [box for k, box in boxes.items() if k not in (src, dst)]
        def crosses(p, q):
            return bool(path_crossings([p, q], boxes, src, dst))
        points = [a, (sx, (sy + ty) / 2), (tx, (sy + ty) / 2), b]
        method = "vertical_cubic"
        if crosses(a, b) and src != dst:
            candidates = []
            for delta in (28, 56, 84, 112, 152, 200):
                candidates.extend([min(sx - sw / 2, tx - tw / 2) - delta,
                                   max(sx + sw / 2, tx + tw / 2) + delta])
            for channel in sorted(candidates, key=lambda x: abs(x - (sx + tx) / 2)):
                channel = max(left + 8, min(right - 8, channel))
                left_path = [(sx - sw / 2, sy), (channel, sy), (channel, ty), (tx - tw / 2, ty)]
                right_path = [(sx + sw / 2, sy), (channel, sy), (channel, ty), (tx + tw / 2, ty)]
                candidate = right_path if channel >= (sx + tx) / 2 else left_path
                source_x = sx + sw / 2 if channel >= (sx + tx) / 2 else sx - sw / 2
                # A neighboring node can block the same-row entry. Try a true
                # outside channel with entry from above/below the target as well.
                alternatives = [candidate]
                for approach in (-1, 1):
                    target_edge_y = ty + approach * th / 2
                    outside_y = target_edge_y + approach * 18
                    alternatives.append([(source_x, sy), (channel, sy),
                                         (channel, outside_y), (tx, outside_y),
                                         (tx, target_edge_y)])
                for alternative in alternatives:
                    if self_intersections(alternative) or path_crossings(alternative, boxes, src, dst):
                        continue
                    points = alternative
                    method = "orthogonal_avoidance"
                    break
                if method == "orthogonal_avoidance":
                    break
        check_points = cubic_points(*points) if method == "vertical_cubic" else points
        crossing_nodes = path_crossings(check_points, boxes, src, dst)
        # Shapely verification is optional; the native segment test above is exact.
        try:
            from shapely.geometry import LineString
            line = LineString(check_points)
            shapely_simple = bool(line.is_simple)
        except ImportError:
            shapely_simple = None
        flat = [v for point in check_points for v in point]
        bbox = [min(flat[::2]), min(flat[1::2]), max(flat[::2]), max(flat[1::2])]
        output[edge["id"]] = {"points": points, "sampled_points": check_points,
                              "bbox": bbox, "method": method,
                              "self_intersections": self_intersections(check_points),
                              "shapely_is_simple": shapely_simple,
                              "source": src, "target": dst,
                              "crossing_nodes": crossing_nodes}
    return output
