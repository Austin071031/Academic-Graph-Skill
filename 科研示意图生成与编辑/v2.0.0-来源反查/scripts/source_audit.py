#!/usr/bin/env python3
"""Deterministic per-element source traceability reverse-check (standard library).

This checks mechanical coverage, file identity, text evidence and rendered SVG IDs.
It never performs or certifies scientific review.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

VERSION = "2.0.0"
LOCATOR_KEYS = ("page", "table", "row", "figure", "panel", "line", "cell")
PATH_KEYS = ("path", "file", "source_path")
HASH_KEYS = ("sha256", "source_sha256")
SUPPORT_KEYS = (
    "quote", "supporting_quote", "supporting_passage", "passage",
    "supporting_text", "value", "supporting_value",
)
TEXT_SUFFIXES = {
    ".md", ".markdown", ".txt", ".text", ".csv", ".tsv", ".json",
    ".jsonl", ".ndjson", ".svg", ".xml", ".yaml", ".yml", ".html",
    ".htm", ".tex", ".bib", ".rst", ".log", ".ini", ".cfg", ".toml",
    ".py", ".r", ".sql", ".fa", ".fasta", ".gff", ".gtf", ".vcf",
    ".sam", ".bed",
}
REVIEW_STATUSES = {"needs_review", "needs_text_or_visual_review"}
UNCERTAIN_MARKERS = {
    "unknown", "uncertain", "source_unknown", "source_uncertain",
    "source-unknown", "source-uncertain", "unresolved", "conflict",
    "conflicting", "unconfirmed", "needs_review", "needs review",
    "tentative", "ambiguous",
}
MAP_METADATA_KEYS = {
    "version", "source_map_version", "schema_version", "metadata",
    "output_version", "created", "created_at", "description",
}


def nonempty(value):
    return value is not None and bool(str(value).strip())


def normalized_id(value):
    if isinstance(value, (str, int)) and not isinstance(value, bool):
        return str(value).strip()
    return ""


def normalize_space(value):
    return re.sub(r"\s+", " ", value).strip()


def support_text(value):
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def first_present(entry, keys):
    for key in keys:
        if key in entry:
            return key, entry[key]
    return None, None


def check(name, status, detail, **extra):
    item = {"check": name, "status": status, "detail": detail}
    item.update(extra)
    return item


def required_spec_elements(spec):
    """Return authored elements and spec-shape checks without inferring science."""
    required = []
    problems = []
    for key, kind in (("nodes", "node"), ("entities", "entity"),
                      ("edges", "edge"), ("groups", "group")):
        value = spec.get(key, [])
        if value is None:
            continue
        if not isinstance(value, list):
            problems.append(check("spec_" + key, "failed", key + " must be a list"))
            continue
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                problems.append(check("spec_" + key, "failed",
                                      "%s[%d] must be an object" % (key, index)))
                continue
            ident = normalized_id(item.get("element_id", item.get("id")))
            required.append({"element_id": ident, "kind": kind,
                             "spec_path": "%s[%d]" % (key, index)})
    for key, kind in (("data_marks", "data_mark"), ("marks", "data_mark"),
                      ("legend", "legend"), ("legends", "legend")):
        value = spec.get(key, [])
        if value is None:
            continue
        if not isinstance(value, list):
            problems.append(check("spec_" + key, "failed", key + " must be a list"))
            continue
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                problems.append(check("spec_" + key, "failed",
                                      "%s[%d] must be an object" % (key, index)))
                continue
            explicitly_bound = item.get("source_bound", item.get("source-bound"))
            if explicitly_bound is None:
                explicitly_bound = any(field in item for field in (
                    "source_id", "source_path", "source_ref", "provenance",
                    "evidence", "citation",
                ))
            if explicitly_bound is True or str(explicitly_bound).lower() == "true":
                ident = normalized_id(item.get("element_id", item.get("id")))
                required.append({"element_id": ident, "kind": kind,
                                 "spec_path": "%s[%d]" % (key, index)})
    seen = {}
    duplicates = []
    for item in required:
        ident = item["element_id"]
        if ident in seen:
            duplicates.append(ident)
        seen[ident] = True
    problems.append(check(
        "spec_unique_ids", "failed" if duplicates else "passed",
        "Duplicate required spec IDs: " + ", ".join(sorted(set(duplicates)))
        if duplicates else "Required spec IDs are unique",
        duplicate_ids=sorted(set(duplicates)),
    ))
    for item in required:
        if not item["element_id"]:
            problems.append(check(
                "spec_element_id", "failed",
                "Missing stable id at " + item["spec_path"],
            ))
    problems.append(check(
        "spec_required_elements_nonempty", "passed" if required else "failed",
        "Authored spec contains source-bound scientific elements"
        if required else
        "No nodes/entities, edges, groups, or explicitly source-bound marks/legends were supplied; provenance coverage cannot pass vacuously",
    ))
    return required, problems


def normalize_map(document):
    """Normalize list, elements list/dict, or straightforward ID-keyed dict."""
    entries = []
    shape_checks = []

    def add(value, map_key=None, location=""):
        if not isinstance(value, dict):
            entries.append({"_invalid": True, "_location": location,
                            "element_id": normalized_id(map_key)})
            shape_checks.append(check("map_entry_shape", "failed",
                                      location + " must be an object"))
            return
        item = dict(value)
        supplied = normalized_id(item.get("element_id", item.get("id")))
        keyed = normalized_id(map_key)
        item["element_id"] = supplied or keyed
        item["_location"] = location
        if supplied and keyed and supplied != keyed:
            item["_key_mismatch"] = keyed
            shape_checks.append(check(
                "map_key_id", "failed",
                "%s ID %r conflicts with key %r" % (location, supplied, keyed),
            ))
        entries.append(item)

    if isinstance(document, list):
        for index, value in enumerate(document):
            add(value, location="root[%d]" % index)
    elif isinstance(document, dict) and "elements" in document:
        elements = document["elements"]
        if isinstance(elements, list):
            for index, value in enumerate(elements):
                add(value, location="elements[%d]" % index)
        elif isinstance(elements, dict):
            for key in sorted(elements):
                add(elements[key], key, "elements." + str(key))
        else:
            shape_checks.append(check("map_elements", "failed",
                                      "elements must be a list or object"))
    elif isinstance(document, dict):
        for key in sorted(document):
            if key in MAP_METADATA_KEYS:
                continue
            add(document[key], key, "root." + str(key))
    else:
        shape_checks.append(check("map_root", "failed",
                                  "Map root must be a list or object"))
    ids = [normalized_id(entry.get("element_id")) for entry in entries]
    duplicate_ids = sorted({ident for ident in ids if ident and ids.count(ident) > 1})
    shape_checks.append(check(
        "map_unique_ids", "failed" if duplicate_ids else "passed",
        "Duplicate map IDs: " + ", ".join(duplicate_ids)
        if duplicate_ids else "Map IDs are unique",
        duplicate_ids=duplicate_ids,
    ))
    return entries, shape_checks


def get_source_path(entry, map_path):
    key, value = first_present(entry, PATH_KEYS)
    if value is None and isinstance(entry.get("source"), dict):
        key, value = first_present(entry["source"], ("path",))
        if key is not None:
            key = "source.path"
    if not nonempty(value):
        return key, None, None
    raw = pathlib.Path(str(value)).expanduser()
    resolved = raw if raw.is_absolute() else map_path.parent / raw
    return key, str(value), resolved


def get_declared_hash(entry):
    key, value = first_present(entry, HASH_KEYS)
    return key, str(value).strip().lower() if nonempty(value) else ""


def get_locator(entry):
    locator = entry.get("locator")
    if isinstance(locator, dict):
        values = {key: locator[key] for key in LOCATOR_KEYS
                  if key in locator and nonempty(locator[key])}
    else:
        values = {}
    if not values:
        values = {key: entry[key] for key in LOCATOR_KEYS
                  if key in entry and nonempty(entry[key])}
    return values


def is_not_applicable(entry, support_key, support_value):
    if support_key and isinstance(support_value, str):
        if support_value.strip().lower() == "not_applicable":
            return True
    for key in ("support", "supporting_evidence"):
        value = entry.get(key)
        if isinstance(value, str) and value.strip().lower() == "not_applicable":
            return True
        if isinstance(value, dict) and str(value.get("status", "")).strip().lower() == "not_applicable":
            return True
    return False


def uncertainty_markers(entry):
    status = str(entry.get("status", "")).strip().lower()
    interpretation = str(entry.get("interpretation", "")).strip().lower()
    markers = []
    for marker in sorted(UNCERTAIN_MARKERS):
        pattern = r"(?<![a-z0-9_])" + re.escape(marker) + r"(?![a-z0-9_])"
        if re.search(pattern, status) or re.search(pattern, interpretation):
            markers.append(marker)
    return markers


def svg_ids(svg_path):
    root = ET.parse(str(svg_path)).getroot()
    return {element.get("id") for element in root.iter()
            if nonempty(element.get("id"))}


def new_element(ident, kind, spec_item=None):
    return {
        "element_id": ident or None,
        "kind": kind,
        "spec_path": spec_item.get("spec_path") if spec_item else None,
        "in_spec": spec_item is not None,
        "status": "failed",
        "mechanical_status": "failed",
        "checks": [],
    }


def audit_entry(entry, spec_item, map_path, rendered_ids, svg_error):
    ident = normalized_id(entry.get("element_id"))
    kind = spec_item["kind"] if spec_item else "unreferenced_map_entry"
    result = new_element(ident, kind, spec_item)
    checks = result["checks"]
    if entry.get("_invalid"):
        checks.append(check("map_entry", "failed", "Map entry is not an object"))
        return result
    key_mismatch = entry.get("_key_mismatch")
    checks.append(check(
        "map_entry", "failed" if not ident or key_mismatch else "passed",
        "Map entry is missing a stable element_id/id" if not ident else
        "Map key conflicts with element ID: " + str(key_mismatch) if key_mismatch
        else "Corresponding map entry found",
        map_location=entry.get("_location"),
    ))
    result["declared_status"] = entry.get("status")
    result["interpretation"] = entry.get("interpretation")
    interpretation_ok = isinstance(entry.get("interpretation"), str) and nonempty(entry.get("interpretation"))
    status_ok = isinstance(entry.get("status"), str) and nonempty(entry.get("status"))
    checks.append(check(
        "interpretation", "passed" if interpretation_ok else "failed",
        "Nonempty interpretation recorded" if interpretation_ok
        else "A nonempty interpretation is required",
    ))
    checks.append(check(
        "declared_status", "passed" if status_ok else "failed",
        "Nonempty source relationship status recorded" if status_ok
        else "A nonempty source relationship status is required",
    ))
    markers = uncertainty_markers(entry)
    result["source_certainty"] = "uncertain" if markers else "not_marked_uncertain"
    result["uncertainty_markers"] = markers
    checks.append(check(
        "source_certainty", "needs_review" if markers else "passed",
        "Declared unknown/uncertain source relationship preserved for review: " +
        ", ".join(markers) if markers else "No declared uncertainty marker",
    ))

    source_key, declared_path, resolved = get_source_path(entry, map_path)
    result["source"] = {"path": declared_path, "resolved_path": str(resolved) if resolved else None}
    path_ok = resolved is not None
    checks.append(check(
        "source_path", "passed" if path_ok else "failed",
        "Source path field: " + str(source_key) if path_ok
        else "Missing path/file/source_path or source.path",
    ))
    actual_hash = None
    source_bytes = None
    exists = bool(resolved and resolved.is_file())
    checks.append(check(
        "source_exists", "passed" if exists else "failed",
        "Source file exists and is a regular file" if exists
        else "Source file is missing or not a regular file",
    ))
    if exists:
        try:
            source_bytes = resolved.read_bytes()
            actual_hash = hashlib.sha256(source_bytes).hexdigest()
        except OSError as exc:
            checks.append(check("source_read", "failed", str(exc)))
    result["source"]["actual_sha256"] = actual_hash
    hash_key, declared_hash = get_declared_hash(entry)
    result["source"]["declared_sha256"] = declared_hash or None
    hash_format_ok = bool(re.fullmatch(r"[0-9a-f]{64}", declared_hash))
    if actual_hash is None:
        hash_status = "not_run"
        detail = "Current SHA256 unavailable because the source could not be read"
    elif not hash_format_ok:
        hash_status = "failed"
        detail = "Declared sha256/source_sha256 is missing or not 64 hexadecimal characters"
    elif declared_hash != actual_hash:
        hash_status = "failed"
        detail = "Current source SHA256 does not match declared hash"
    else:
        hash_status = "passed"
        detail = "Current source SHA256 independently matches " + str(hash_key)
    checks.append(check("source_sha256", hash_status, detail))

    locator = get_locator(entry)
    result["locator"] = locator
    checks.append(check(
        "locator", "passed" if locator else "failed",
        "Locator fields: " + ", ".join(sorted(locator)) if locator
        else "Missing precise locator: page/table/row/figure/panel/line/cell",
    ))
    support_key, support_value = first_present(entry, SUPPORT_KEYS)
    pure_geometry = is_not_applicable(entry, support_key, support_value)
    support_ok = pure_geometry or (support_key is not None and nonempty(support_value))
    checks.append(check(
        "supporting_evidence", "passed" if support_ok else "failed",
        "Explicit not_applicable recorded for pure geometry" if pure_geometry else
        "Supporting evidence field: " + str(support_key) if support_ok else
        "Missing supporting passage/value or explicit not_applicable for pure geometry",
    ))
    result["support_field"] = support_key
    result["pure_geometry_not_applicable"] = pure_geometry

    suffix = resolved.suffix.lower() if resolved else ""
    is_text = suffix in TEXT_SUFFIXES
    result["source"]["text_class"] = "utf8_text_like" if is_text else "pdf_or_binary_or_unknown"
    if pure_geometry:
        checks.append(check("quote_match", "not_applicable",
                            "No quote is required for declared pure geometry"))
    elif support_ok and source_bytes is not None:
        if is_text:
            try:
                source_text = source_bytes.decode("utf-8")
                haystack = normalize_space(source_text)
                needle = normalize_space(support_text(support_value))
                matched = needle in haystack
                checks.append(check(
                    "quote_match", "passed" if matched else "failed",
                    "Supporting text occurs exactly after whitespace normalization"
                    if matched else
                    "Supporting text/value does not occur after whitespace normalization",
                    support_field=support_key,
                ))
            except (UnicodeDecodeError, AttributeError) as exc:
                checks.append(check("quote_match", "failed",
                                    "Text-like source is not valid UTF-8: " + str(exc)))
        else:
            checks.append(check(
                "quote_match", "needs_text_or_visual_review",
                "Existence, hash and locator checked; PDF/binary/unknown text was not mechanically matched",
                support_field=support_key,
            ))
    else:
        checks.append(check("quote_match", "not_run",
                            "Quote check requires supporting evidence and readable source bytes"))

    if rendered_ids is not None or svg_error is not None:
        if spec_item is None:
            checks.append(check("svg_id", "not_applicable",
                                "Map entry is not a required spec element"))
        elif svg_error is not None:
            checks.append(check("svg_id", "failed",
                                "SVG could not be parsed: " + svg_error))
        elif not ident:
            checks.append(check("svg_id", "failed",
                                "Required spec element has no stable ID to find in SVG"))
        elif ident in rendered_ids:
            checks.append(check("svg_id", "passed", "Required ID appears as an SVG XML id attribute"))
        else:
            checks.append(check("svg_id", "failed", "Required ID is absent from rendered SVG XML"))
    result["mechanical_status"] = (
        "failed" if any(item["status"] == "failed" for item in checks) else "passed"
    )
    result["status"] = (
        "failed" if result["mechanical_status"] == "failed" else
        "needs_review" if any(item["status"] in REVIEW_STATUSES for item in checks)
        else "passed"
    )
    return result


def unmapped_element(spec_item, rendered_ids, svg_error):
    result = new_element(spec_item["element_id"], spec_item["kind"], spec_item)
    result["checks"].append(check("map_entry", "failed",
                                  "Required authored spec element has no corresponding map entry"))
    if rendered_ids is not None or svg_error is not None:
        ident = spec_item["element_id"]
        if svg_error is not None:
            status, detail = "failed", "SVG could not be parsed: " + svg_error
        elif not ident:
            status, detail = "failed", "Required spec element has no stable ID to find in SVG"
        elif ident in rendered_ids:
            status, detail = "passed", "Required ID appears as an SVG XML id attribute"
        else:
            status, detail = "failed", "Required ID is absent from rendered SVG XML"
        result["checks"].append(check("svg_id", status, detail))
    return result


def summarize(global_checks, elements, required_count, unmapped_count, extra_count):
    all_checks = list(global_checks)
    for element in elements:
        all_checks.extend(element["checks"])
    statuses = ("passed", "failed", "needs_review", "needs_text_or_visual_review",
                "not_applicable", "not_run")
    check_counts = {name: sum(item["status"] == name for item in all_checks)
                   for name in statuses}
    element_counts = {name: sum(item["status"] == name for item in elements)
                     for name in ("passed", "failed", "needs_review")}
    failed = check_counts["failed"] > 0 or element_counts["failed"] > 0
    missing_svg = sum(
        item["check"] == "svg_id" and item["status"] == "failed" and
        "absent" in item["detail"]
        for item in all_checks
    )
    summary = {
        "required_elements": required_count,
        "mapped_required_elements": required_count - unmapped_count,
        "unmapped_required_elements": unmapped_count,
        "extra_map_entries": extra_count,
        "audited_elements": len(elements),
        "elements_passed": element_counts["passed"],
        "elements_failed": element_counts["failed"],
        "elements_needing_review": element_counts["needs_review"],
        "uncertain_elements": sum(item.get("source_certainty") == "uncertain" for item in elements),
        "missing_svg_ids": missing_svg,
        "checks_total": len(all_checks),
    }
    summary.update({"checks_" + name: count for name, count in check_counts.items()})
    summary["checks_needing_review"] = sum(check_counts[name] for name in REVIEW_STATUSES)
    summary["mechanical_checks_passed"] = not failed
    return summary


def base_report(args):
    return {
        "audit": "deterministic_independent_per_element_source_traceability",
        "version": VERSION,
        "status": "failed",
        "inputs": {"spec": args.spec, "map": args.map, "svg": args.svg},
        "scientific_review": "not_performed",
        "checks": [],
        "elements": [],
        "unmapped_elements": [],
        "extra_map_entries": [],
        "summary": summarize([], [], 0, 0, 0),
    }


def run_audit(args):
    report = base_report(args)
    try:
        spec_path = pathlib.Path(args.spec)
        map_path = pathlib.Path(args.map)
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        if not isinstance(spec, dict):
            raise ValueError("Spec root must be an object")
        report["checks"].append(check("spec_parse", "passed", "Spec JSON parsed"))
        map_document = json.loads(map_path.read_text(encoding="utf-8"))
        report["checks"].append(check("map_parse", "passed", "Source map JSON parsed"))
        required, spec_checks = required_spec_elements(spec)
        entries, map_checks = normalize_map(map_document)
        report["checks"].extend(spec_checks)
        report["checks"].extend(map_checks)

        rendered_ids = None
        svg_error = None
        if args.svg:
            try:
                rendered_ids = svg_ids(pathlib.Path(args.svg))
                report["checks"].append(check("svg_parse", "passed",
                                              "SVG XML parsed; matching uses id attributes"))
            except (ET.ParseError, OSError) as exc:
                svg_error = str(exc)
                report["checks"].append(check("svg_parse", "failed", svg_error))

        by_id = {}
        for item in required:
            by_id.setdefault(item["element_id"], item)
        mapped_ids = set()
        elements = []
        for entry in entries:
            ident = normalized_id(entry.get("element_id"))
            spec_item = by_id.get(ident)
            if spec_item is not None:
                mapped_ids.add(ident)
            elements.append(audit_entry(entry, spec_item, map_path, rendered_ids, svg_error))
        unmapped = [item for item in required if item["element_id"] not in mapped_ids]
        for item in unmapped:
            elements.append(unmapped_element(item, rendered_ids, svg_error))
        required_identities = {(item["kind"], item["spec_path"]) for item in required}
        extra = [normalized_id(entry.get("element_id")) for entry in entries
                 if normalized_id(entry.get("element_id")) not in by_id]
        report["elements"] = elements
        report["unmapped_elements"] = [
            {"element_id": item["element_id"] or None, "kind": item["kind"],
             "spec_path": item["spec_path"]} for item in unmapped
        ]
        report["extra_map_entries"] = extra
        report["summary"] = summarize(report["checks"], elements,
                                       len(required_identities), len(unmapped), len(extra))
        report["status"] = "failed" if not report["summary"]["mechanical_checks_passed"] else "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
        report["checks"].append(check("audit_execution", "failed", str(exc)))
        report["summary"] = summarize(report["checks"], report["elements"], 0, 0, 0)
    return report


def write_report(path, report):
    destination = pathlib.Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(destination)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", required=True, help="Authored figure_spec.json")
    parser.add_argument("--map", required=True, help="Element source_map.json")
    parser.add_argument("--out", required=True, help="Always-written source_checks.json")
    parser.add_argument("--svg", help="Optional rendered SVG for exact XML ID checks")
    args = parser.parse_args(argv)
    report = run_audit(args)
    try:
        write_report(args.out, report)
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc),
                          "report": args.out}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"status": report["status"], "output": args.out,
                      "summary": report["summary"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
