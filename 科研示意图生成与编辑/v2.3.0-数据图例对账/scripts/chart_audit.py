#!/usr/bin/env python3
"""Independently reload chart source cells and audit values, marks, and legends.

Python 3.8+ standard library; XLSX is optional and requires preinstalled openpyxl.
The map describes chart encodings; this helper does not infer scientific meaning.
"""
import argparse
import csv
import decimal
import hashlib
import importlib.util
import io
import json
import pathlib
import sys


REPORT_SCHEMA = "chart-audit-report-1"
CELL_FIELDS = ("file", "sha256", "raw_value")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path, value):
    destination = pathlib.Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def is_missing(value):
    """Only explicit blanks/null are missing; numeric zero is never missing."""
    return value is None or (isinstance(value, str) and value == "")


def decimal_value(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float, decimal.Decimal)):
        text = str(value)
    elif isinstance(value, str):
        text = value.strip()
    else:
        return None
    if not text:
        return None
    try:
        number = decimal.Decimal(text)
    except decimal.InvalidOperation:
        return None
    return number if number.is_finite() else None


def values_equal(left, right):
    """Use exact decimal comparison for numbers, exact equality otherwise."""
    if is_missing(left) or is_missing(right):
        return is_missing(left) and is_missing(right)
    left_number, right_number = decimal_value(left), decimal_value(right)
    if left_number is not None and right_number is not None:
        return left_number == right_number
    return type(left) is type(right) and left == right


def typed_value(value):
    """Report a typed value without conflating blank, null, and zero."""
    if is_missing(value):
        return None
    number = decimal_value(value)
    return number if number is not None else value


class Audit:
    def __init__(self, map_path, map_data):
        self.map_path = pathlib.Path(map_path).resolve()
        self.base = self.map_path.parent
        self.data = map_data
        self.checks = []
        self.sources = {}
        self.reverse = {}
        self.records = []
        self.counter = 0

    def check(self, kind, passed, **details):
        self.counter += 1
        item = {
            "id": "check-%04d" % self.counter,
            "kind": kind,
            "mechanical": True,
            "status": "passed" if passed else "failed",
        }
        item.update(details)
        self.checks.append(item)
        return item["id"]

    def source(self, filename):
        path = pathlib.Path(filename)
        if not path.is_absolute():
            path = self.base / path
        path = path.resolve()
        key = str(path)
        if key in self.sources:
            return self.sources[key]
        entry = {"path": path, "suffix": path.suffix.lower(), "loaded": False}
        try:
            entry["actual_sha256"] = sha256_file(path)
            suffix = entry["suffix"]
            if suffix in (".csv", ".tsv"):
                text = path.read_text(encoding="utf-8-sig")
                delimiter = "\t" if suffix == ".tsv" else ","
                entry["content"] = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
                entry["loaded"] = True
            elif suffix == ".json":
                content = json.loads(path.read_text(encoding="utf-8-sig"), parse_float=decimal.Decimal)
                if not isinstance(content, list):
                    raise ValueError("JSON chart source root must be an array")
                entry["content"] = content
                entry["loaded"] = True
            elif suffix == ".xlsx":
                if importlib.util.find_spec("openpyxl") is None:
                    entry["error"] = "XLSX unsupported: optional openpyxl is not installed"
                    entry["error_code"] = "xlsx_support_unavailable"
                else:
                    import openpyxl
                    entry["content"] = openpyxl.load_workbook(
                        str(path), read_only=True, data_only=True
                    )
                    entry["loaded"] = True
            else:
                entry["error"] = "Unsupported source format: " + (suffix or "no extension")
                entry["error_code"] = "unsupported_source_format"
        except Exception as exc:
            entry["error"] = "%s: %s" % (type(exc).__name__, exc)
            entry["error_code"] = "source_load_failed"
        self.sources[key] = entry
        return entry

    def csv_cell(self, rows, row, column):
        if not isinstance(row, int) or isinstance(row, bool) or row < 1:
            raise ValueError("CSV/TSV row must be a 1-based integer")
        if not rows:
            raise ValueError("CSV/TSV has no rows")
        if isinstance(column, int) and not isinstance(column, bool):
            index = column - 1
            if index < 0:
                raise ValueError("CSV/TSV column numbers are 1-based")
        elif isinstance(column, str):
            headers = rows[0]
            matches = [i for i, header in enumerate(headers) if header == column]
            if len(matches) != 1:
                raise ValueError("CSV/TSV column must match one unique header")
            index = matches[0]
        else:
            raise ValueError("CSV/TSV column must be a header or 1-based integer")
        if row > len(rows) or index >= len(rows[row - 1]):
            raise ValueError("CSV/TSV cell is outside the loaded table")
        return rows[row - 1][index]

    @staticmethod
    def json_cell(content, row, column):
        if not isinstance(row, int) or isinstance(row, bool) or row < 1:
            raise ValueError("JSON row must be a 1-based array-item integer")
        if row > len(content):
            raise ValueError("JSON row is outside the root array")
        item = content[row - 1]
        if isinstance(item, dict):
            if column not in item:
                raise ValueError("JSON object key is absent")
            return item[column]
        if isinstance(item, list):
            if not isinstance(column, int) or isinstance(column, bool) or column < 1:
                raise ValueError("JSON nested-array column must be a 1-based integer")
            if column > len(item):
                raise ValueError("JSON column is outside the nested array")
            return item[column - 1]
        raise ValueError("JSON row must locate an object or nested array")

    @staticmethod
    def json_pointer(content, pointer):
        if not isinstance(pointer, str) or not pointer.startswith("/"):
            raise ValueError("JSON pointer must begin with '/'")
        current = content
        for token in pointer[1:].split("/"):
            token = token.replace("~1", "/").replace("~0", "~")
            if isinstance(current, list):
                if not token.isdigit():
                    raise ValueError("JSON array pointer token must be a nonnegative integer")
                index = int(token)
                if index >= len(current):
                    raise ValueError("JSON pointer array index is absent")
                current = current[index]
            elif isinstance(current, dict):
                if token not in current:
                    raise ValueError("JSON pointer object key is absent")
                current = current[token]
            else:
                raise ValueError("JSON pointer traverses a scalar")
        return current

    def load_cell(self, cell, source):
        suffix = source["suffix"]
        if suffix in (".csv", ".tsv"):
            actual = self.csv_cell(source["content"], cell.get("row"), cell.get("column"))
        elif suffix == ".json":
            pointer = cell.get("json_pointer", cell.get("pointer"))
            if pointer is not None:
                actual = self.json_pointer(source["content"], pointer)
            else:
                actual = self.json_cell(source["content"], cell.get("row"), cell.get("column"))
        elif suffix == ".xlsx":
            workbook = source["content"]
            sheet_name = cell.get("sheet") or workbook.active.title
            if sheet_name not in workbook.sheetnames:
                raise ValueError("XLSX sheet is absent")
            sheet = workbook[sheet_name]
            row, column = cell.get("row"), cell.get("column")
            if not isinstance(row, int) or isinstance(row, bool) or row < 1:
                raise ValueError("XLSX row must be a 1-based integer")
            if isinstance(column, str):
                letters = column.upper()
                if not letters or any(letter < "A" or letter > "Z" for letter in letters):
                    raise ValueError("XLSX column letters must contain only A-Z")
                column_number = 0
                for letter in letters:
                    column_number = column_number * 26 + ord(letter) - 64
                column = column_number
            elif not isinstance(column, int) or isinstance(column, bool) or column < 1:
                raise ValueError("XLSX column must be letters or a 1-based integer")
            actual = sheet.cell(row=row, column=column).value
        else:
            raise ValueError("No loader for source format")
        if isinstance(actual, (dict, list)):
            raise ValueError("Source cell must locate a scalar, not an object/array")
        return actual

    def locator(self, cell, source):
        return {
            "file": str(source["path"]),
            "sheet": cell.get("sheet"),
            "row": cell.get("row"),
            "column": cell.get("column"),
            "json_pointer": cell.get("json_pointer", cell.get("pointer")),
        }

    def raw_cell(self, record, record_type, cell, cell_index):
        context = {"record_type": record_type, "record_id": record["id"], "cell_index": cell_index}
        missing_fields = [name for name in CELL_FIELDS if name not in cell]
        needs_locator = not isinstance(cell, dict) or (
            "json_pointer" not in cell
            and "pointer" not in cell
            and ("row" not in cell or "column" not in cell)
        )
        if missing_fields or needs_locator:
            self.check(
                "source_cell.schema",
                False,
                **dict(context, expected="file, sha256, raw_value, and a cell locator", missing_fields=missing_fields)
            )
            return None, _UNLOADED
        source = self.source(cell["file"])
        location = self.locator(cell, source)
        context["locator"] = location
        declared_hash = cell.get("sha256")
        hash_ok = (
            isinstance(declared_hash, str)
            and source.get("actual_sha256") is not None
            and declared_hash.lower() == source["actual_sha256"]
        )
        self.check(
            "source.sha256", hash_ok, **dict(context, expected=declared_hash, actual=source.get("actual_sha256"))
        )
        reverse_key = json.dumps(location, ensure_ascii=False, sort_keys=True)
        reverse = self.reverse.setdefault(
            reverse_key,
            {"locator": location, "actual_sha256": source.get("actual_sha256"), "references": []},
        )
        reference = {"record_type": record_type, "record_id": record["id"], "cell_index": cell_index}
        reverse["references"].append(reference)
        if not source.get("loaded"):
            self.check(
                "source.load", False,
                **dict(context, error_code=source.get("error_code"), error=source.get("error"))
            )
            return source, _UNLOADED
        try:
            actual = self.load_cell(cell, source)
        except Exception as exc:
            self.check("source.locator", False, **dict(context, error=str(exc)))
            return source, _UNLOADED
        expected = cell.get("raw_value")
        raw_ok = values_equal(actual, expected)
        raw_check = self.check(
            "source.raw_value", raw_ok,
            **dict(context, expected_raw=expected, actual_raw=actual,
                   comparison="exact decimal for finite numerics; exact value otherwise")
        )
        reference["raw_check"] = raw_check
        reference["actual_raw"] = actual
        return source, actual

    @staticmethod
    def item_parts(item, index, cells):
        if isinstance(item, dict):
            cell_index = item.get("cell", index)
            if "value" in item:
                value = item["value"]
            else:
                value = item.get("encoded_value")
            return cell_index, value, item
        return index, item, {}

    def encoded_items(self, record, record_type, cells, raw_values, collection_name):
        items = record[collection_name]
        expected_typed = []
        for index, item in enumerate(items):
            cell_index, value, properties = self.item_parts(item, index, cells)
            context = {
                "record_type": record_type, "record_id": record["id"],
                "collection": collection_name, "item_index": index,
                "cell_index": cell_index,
            }
            if isinstance(item, dict) and "value" not in item and "encoded_value" not in item:
                self.check(collection_name + ".encoding_schema", False,
                           **dict(context, error="Encoded entry needs a value (marks may use encoded_value)"))
                continue
            valid_cell = (
                isinstance(cell_index, int) and not isinstance(cell_index, bool)
                and 0 <= cell_index < len(cells)
            )
            if not valid_cell:
                self.check(collection_name + ".cell_reference", False, **dict(context, error="Cell index is absent or outside source_cells"))
                continue
            if cell_index >= len(raw_values) or raw_values[cell_index] is _UNLOADED:
                self.check(collection_name + ".source_unavailable", False, **context)
                continue
            raw = raw_values[cell_index]
            equal = values_equal(value, raw)
            missing_ok = (raw is not _UNLOADED) and (
                (is_missing(raw) and value is None)
                or (not is_missing(raw) and value is not None and not is_missing(value))
            )
            expected_typed.append((cell_index, typed_value(value)))
            self.check(
                collection_name + ".source_match", equal and missing_ok,
                **dict(context, actual_encoded=value, source_raw=raw,
                       expected_typed=typed_value(raw), missing_source=is_missing(raw),
                       missing_encoded=is_missing(value))
            )
            cell = cells[cell_index]
            if "unit" in cell or "unit" in record:
                expected_unit = cell["unit"] if "unit" in cell else record.get("unit")
                actual_unit = properties.get("unit", record.get("unit", _ABSENT))
                unit_ok = actual_unit is not _ABSENT and actual_unit == expected_unit
                self.check(
                    collection_name + ".unit", unit_ok,
                    **dict(context, expected=expected_unit,
                           actual=None if actual_unit is _ABSENT else actual_unit,
                           inherited_from_record=actual_unit is not _ABSENT and "unit" not in properties and "unit" in record)
                )
            if collection_name == "marks":
                expected_style = dict(record.get("legend") or {})
                expected_style.update(record.get("style") or {})
                mark_style = dict(properties.get("style") or {})
                for prop in ("color", "marker"):
                    if prop in properties:
                        mark_style[prop] = properties[prop]
                for prop, actual_style in mark_style.items():
                    if prop in expected_style:
                        self.check(
                            "mark.style", actual_style == expected_style[prop],
                            **dict(context, property=prop, expected=expected_style[prop], actual=actual_style)
                        )
        return expected_typed

    def audit_record(self, record, record_type):
        if not isinstance(record, dict):
            self.check("record.schema", False, record_type=record_type, error="Record must be an object")
            return
        required = ("id", "source_cells", "values", "marks", "legend")
        absent = [key for key in required if key not in record]
        valid = not absent and isinstance(record.get("id"), str) and bool(record.get("id"))
        valid = valid and isinstance(record.get("source_cells"), list) and bool(record.get("source_cells"))
        valid = valid and isinstance(record.get("values"), list) and isinstance(record.get("marks"), list)
        valid = valid and isinstance(record.get("legend"), dict)
        valid = valid and ("style" not in record or isinstance(record.get("style"), dict))
        if not valid:
            self.check("record.schema", False, record_type=record_type, record_id=record.get("id"), missing_fields=absent,
                       error="Record needs id, nonempty source_cells, values/marks arrays, legend object, and object style when present")
            return
        self.records.append((record_type, record))
        cells = record["source_cells"]
        raw_values = []
        for index, cell in enumerate(cells):
            if not isinstance(cell, dict):
                self.check("source_cell.schema", False, record_type=record_type, record_id=record["id"], cell_index=index,
                           error="Source cell must be an object")
                raw_values.append(_UNLOADED)
                continue
            _, actual = self.raw_cell(record, record_type, cell, index)
            raw_values.append(actual)
        values = self.encoded_items(record, record_type, cells, raw_values, "values")
        marks = self.encoded_items(record, record_type, cells, raw_values, "marks")
        for collection_name, encoded in (("values", values), ("marks", marks)):
            covered_cells = {index for index, _ in encoded}
            for index, _ in enumerate(cells):
                self.check(
                    collection_name + ".cell_coverage", index in covered_cells,
                    record_type=record_type, record_id=record["id"], cell_index=index,
                    error=None if index in covered_cells else "No " + collection_name + " entry corresponds to this source cell"
                )
        # Keep references useful for tracing each value and mark back to its raw cell.
        for collection_name in ("values", "marks"):
            for item_index, item in enumerate(record[collection_name]):
                cell_index, _, _ = self.item_parts(item, item_index, cells)
                if isinstance(cell_index, int) and not isinstance(cell_index, bool) and 0 <= cell_index < len(cells):
                    self.add_encoded_reference(record_type, record["id"], cells[cell_index], cell_index,
                                               collection_name, item_index)

    def add_encoded_reference(self, record_type, record_id, cell, cell_index, collection, item_index):
        if not isinstance(cell, dict) or "file" not in cell:
            return
        source = self.source(cell["file"])
        key = json.dumps(self.locator(cell, source), ensure_ascii=False, sort_keys=True)
        if key in self.reverse:
            for reference in self.reverse[key]["references"]:
                if (reference["record_type"] == record_type and reference["record_id"] == record_id
                        and reference["cell_index"] == cell_index):
                    reference.setdefault("encoded", []).append(
                        {"collection": collection, "item_index": item_index}
                    )

    def audit_legend_and_style(self):
        legend = self.data.get("legend")
        if not isinstance(legend, list):
            self.check("legend.schema", False, expected="Top-level legend array", actual=legend)
            return
        identifiers = [record["id"] for _, record in self.records]
        expected_by_id = {record["id"]: record for _, record in self.records}
        self.check("legend.count", len(legend) == len(self.records), expected=len(self.records), actual=len(legend))
        self.check("legend.unique_ids", len(identifiers) == len(set(identifiers)), actual=identifiers)
        seen = []
        for index, entry in enumerate(legend):
            context = {"legend_index": index}
            if not isinstance(entry, dict):
                self.check("legend.schema", False, **dict(context, error="Legend entry must be an object"))
                continue
            record_id = entry.get("series", entry.get("record"))
            seen.append(record_id)
            if record_id not in expected_by_id:
                self.check("legend.series", False, **dict(context, actual=record_id, expected_known_ids=identifiers))
                continue
            record = expected_by_id[record_id]
            expected = record["legend"]
            for prop in ("label", "color", "marker"):
                if prop not in expected:
                    self.check("legend.expected_property", False, **dict(context, series=record_id, property=prop,
                                                                         error="Record legend must declare label/color/marker"))
                else:
                    self.check("legend." + prop, entry.get(prop, _ABSENT) == expected[prop],
                               **dict(context, series=record_id, expected=expected[prop],
                                      actual=None if entry.get(prop, _ABSENT) is _ABSENT else entry.get(prop)))
            if index < len(self.records):
                ordered_id = self.records[index][1]["id"]
                self.check("legend.order", record_id == ordered_id,
                           **dict(context, expected=ordered_id, actual=record_id))
        self.check("legend.category_coverage", set(seen) == set(identifiers) and len(seen) == len(identifiers),
                   expected=identifiers, actual=seen)
        style_root = self.data.get("style", {})
        series_styles = style_root.get("series", {}) if isinstance(style_root, dict) else {}
        if not isinstance(series_styles, dict):
            self.check("style.schema", False, error="style.series must be an object keyed by series id")
            return
        for record_type, record in self.records:
            record_id = record["id"]
            expected_style = record.get("style", {})
            if not isinstance(expected_style, dict):
                self.check("style.expected_schema", False, series=record_id, error="Record style must be an object")
                continue
            actual_style = series_styles.get(record_id, {})
            if expected_style and not isinstance(actual_style, dict):
                self.check("style.series_schema", False, series=record_id, actual=actual_style)
                continue
            for prop, expected_value in expected_style.items():
                actual_value = actual_style.get(prop, _ABSENT) if isinstance(actual_style, dict) else _ABSENT
                self.check("style.series", actual_value == expected_value,
                           series=record_id, record_type=record_type, property=prop,
                           expected=expected_value, actual=None if actual_value is _ABSENT else actual_value)

    def run(self):
        if not isinstance(self.data, dict):
            self.check("map.schema", False, error="Map root must be an object")
            return self.report()
        collections = []
        for record_type in ("series", "elements"):
            records = self.data.get(record_type, [])
            if not isinstance(records, list):
                self.check("map." + record_type, False, error=record_type + " must be an array")
            else:
                collections.extend((record, record_type) for record in records)
        if not collections:
            self.check("map.records", False, error="At least one series/elements record is required")
        for record, record_type in collections:
            self.audit_record(record, record_type)
        self.audit_legend_and_style()
        if not self.checks:
            self.check("audit.nonempty", False, error="No mechanical checks were generated")
        return self.report()

    def report(self):
        failed = sum(check["status"] == "failed" for check in self.checks if check.get("mechanical"))
        status = "passed" if self.checks and failed == 0 else "failed"
        sources = []
        for path, source in self.sources.items():
            sources.append({
                "file": path, "actual_sha256": source.get("actual_sha256"),
                "loaded": source.get("loaded", False), "format": source.get("suffix"),
                "error_code": source.get("error_code"), "error": source.get("error"),
            })
        return {
            "schema_version": REPORT_SCHEMA,
            "map": str(self.map_path),
            "status": status,
            "summary": {
                "checks_total": len(self.checks),
                "mechanical_checks": sum(bool(c.get("mechanical")) for c in self.checks),
                "mechanical_failed": failed,
                "mechanical_passed": sum(c.get("mechanical") and c["status"] == "passed" for c in self.checks),
            },
            "checks": self.checks,
            "sources": sources,
            "reverse_cell_index": self.reverse,
            "scientific_review": {
                "status": "not_performed",
                "reason": "Mechanical cell/encoding/legend reconciliation cannot verify scientific interpretation, chart-type appropriateness, statistical claims, or visual fidelity."
            },
        }


_ABSENT = object()
_UNLOADED = object()


def execute(map_path, out_path):
    data = None
    load_error = None
    try:
        data = json.loads(pathlib.Path(map_path).read_text(encoding="utf-8-sig"), parse_float=decimal.Decimal)
    except Exception as exc:
        load_error = "%s: %s" % (type(exc).__name__, exc)
    audit = Audit(map_path, data)
    if load_error:
        audit.check("map.load", False, error=load_error)
        report = audit.report()
    else:
        try:
            report = audit.run()
        except Exception as exc:
            audit.check("audit.internal_error", False, error="%s: %s" % (type(exc).__name__, exc))
            report = audit.report()
    atomic_json(out_path, report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", required=True, dest="map_path", help="Chart map JSON")
    parser.add_argument("--out", required=True, help="Detailed audit report JSON (always written)")
    args = parser.parse_args(argv)
    report = execute(args.map_path, args.out)
    print(json.dumps({"status": report["status"], "output": str(pathlib.Path(args.out).resolve()),
                      "mechanical_failed": report["summary"]["mechanical_failed"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
