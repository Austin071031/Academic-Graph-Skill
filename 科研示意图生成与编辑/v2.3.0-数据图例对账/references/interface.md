# Helper interfaces and synthetic example

`diagram.py` is a deterministic file/render helper. Scientific extraction, layout decisions and final source judgement belong to the executing agent. All output is generated from runtime inputs; the helper contains no biological content.

## Commands

- `inspect --input DIR --out JSON`: relative paths, sizes, hashes, optional tool discovery. Reads files, never guesses science from filenames.
- `render --spec JSON --out SVG`: draw explicitly positioned compartments, nodes, edges and legend with selectable text. Supports arrow, activation, inhibition, association and sequence. `points` overrides routing. Unsupported relations are rejected. Use custom drawing code for other semantics.
- `patch --svg FILE --changes JSON --out SVG`: conservative ID-based attribute/text edits. Refuses duplicate/missing IDs, complex text replacement and unknown patch operations. Writes `OUT.changes.json` with old/new values and hashes; original untouched. Geometry edits require custom code and independent checks.
- `export --svg SVG --dpi NUMBER --out JSON`: try installed exporters; produce same-stem PNG/PDF. Report actual errors and whether files exist. Pillow (if present) records PNG actual size/mode/DPI; pdfinfo/pdffonts record actual PDF measurements. Failure does not delete the SVG.
- `audit --svg SVG --out JSON`: parse SVG, inventory text/group/IDs; warn on raster references, external images, absent text, duplicate IDs, viewBox problems. Does not certify scientific correctness or guarantee collision-free geometry.
- `finalize --case JSON --report JSON --out JSON`: accept authored results, enforce original case_id, check known original output_contract fields, optionally validate actual JSON schema using jsonschema. Missing fields/type errors are fatal; never auto-invent values. Output is atomic.
- `chart_audit.py --map JSON --out JSON`: reload and hash the actual CSV/TSV/JSON-array source files, reconcile raw cells to values/marks and legend/style entries, and emit detailed checks plus a reverse cell index. Optional XLSX works only with preinstalled openpyxl and otherwise reports an explicit failure. Always writes the report; overall pass requires nonempty, all-passing mechanical checks.

## Render spec (SYNTHETIC DEMONSTRATION ONLY)

This invented non-scientific toy illustrates the interface. It is NOT a formal case answer. At runtime build a different spec from actual materials, with correct provenance and physical constraints.

```json
{
  "width": 640, "height": 360, "width_mm": 160, "height_mm": 90,
  "font_family": "DejaVu Sans", "font_size": 16,
  "title": "Synthetic interface demonstration",
  "groups": [{"id":"region","label":"Example region","x":30,"y":60,"w":580,"h":180}],
  "nodes": [
    {"id":"sample","label":"Example input","x":70,"y":125,"w":180,"h":60,"fill":"#DDEAF2"},
    {"id":"review","label":"Example review","x":385,"y":125,"w":180,"h":60,"fill":"#F3E5C7"}
  ],
  "edges": [{"id":"flow","source":"sample","target":"review","kind":"sequence","label":"example transfer"}],
  "legend": [{"label":"Example category","color":"#DDEAF2"}]
}
```

Save that to a temporary `demo.json`, then:
```
python3 scripts/diagram.py render --spec demo.json --out /tmp/demo.svg
python3 scripts/diagram.py export --svg /tmp/demo.svg --dpi 300 --out /tmp/demo-export.json
```
Illustrative output: SVG with editable `sample` and `review` groups, native text and one directional edge; real PNG/PDF if a converter is installed; export JSON lists measured properties or actual failure. No rendered example files are included in the submission.

Nodes require numeric `x,y,w,h`, positive size and unique IDs. Newline labels produce tspans. Groups have the same rectangle coordinates. Edges attach to rectangular node boundaries by default; for custom routes pass `points: [[x,y],...]` starting and ending at actual boundary. Legend items have `label,color`; use explicit source-derived ordering. This renderer provides a palette, not scientific data mapping: the agent must populate colors consistently from runtime data. It cannot draw a scientifically faithful complex mechanism without an authored spec.

Patch input example (synthetic):
```json
[{"id":"sample-label","op":"text","value":"Revised example"},
 {"id":"sample-shape","op":"attrs","value":{"fill":"#CCE4DD"}}]
```
The `text` operation works on simple text or one tspan; a multi-line text tree is deliberately refused to avoid discarding styled content. For real source editing use IDs actually present in the original source, not these synthetic IDs.

## Chart cell/mark/legend audit

Run the independent reload and reconciliation after drawing:
```
python3 /skills/weekly-skill/scripts/chart_audit.py --map /app/output/chart_map.json --out /app/output/chart_checks.json
```
The report is written even when loading or checking fails; failure returns nonzero. `status: passed` requires at least one mechanical check and zero mechanical failures. `scientific_review` remains separately `not_performed`: these checks do not infer axes, statistics, scientific meaning, or visual correctness.

### Reusable map schema

The root has `series` and/or `elements` arrays. Every record has a unique `id`, nonempty `source_cells`, `values`, `marks`, and an expected `legend` object with `label`, `color`, and `marker`. Optional record `unit` and `style` describe expected units/style properties. The root `legend` array records the actual rendered entries in category order, each using `series: RECORD_ID`. `style.series` records actual style properties keyed by series ID. `elements` uses the same record shape for independently mapped marks.

Each source cell declares:

- `file`: actual source path, absolute or relative to the map; `sha256`: expected hash of the actual bytes; `raw_value`: expected snapshot of that cell.
- CSV/TSV: `row` is 1-based with header row 1 and first data row 2. `column` is a unique header string or 1-based integer.
- JSON: the root must be an array. `row` is the 1-based root-array item, and `column` is its object key or 1-based nested-array index. An optional RFC 6901 `json_pointer` (also accepted as `pointer`) is the precise locator and takes precedence over row/column.
- XLSX: optional `sheet` (otherwise active sheet), 1-based `row`, and column letters or 1-based number. Loading requires preinstalled openpyxl; the standard-library-only installation reports `xlsx_support_unavailable` rather than silently skipping the cell.

`values` and `marks` align positionally with `source_cells` by default. An object entry can set a zero-based `cell` index explicitly. Values use `value`; marks use `encoded_value` (or `value`). Scalars are shorthand. Axes/geometry are not inferred: `encoded_value` is the actual numeric or categorical value encoded by the authored bar/point/etc. Use JSON `null` for a missing value or mark. A blank source cell is missing; numeric zero is not. Finite numeric comparisons use `Decimal`, without float tolerances; other values compare exactly.

Declare units on source cells/records and on value/mark entries when applicable; entries inherit record units, and declared units must match exactly. Do not invent a unit for an undeclared source. Optional mark `color`/`marker` or `style` properties are checked against expected series legend/style. The root legend count, order, category coverage, label/color/marker, and `style.series` expected properties are mechanical checks. The reverse cell index links every raw locator back to record/value/mark references.

### Synthetic map demonstration only

This non-scientific toy is an interface example, not case data. Replace paths, hashes, cells, and authored encodings from actual runtime materials before use.

```json
{
  "series": [
    {
      "id": "A", "unit": "u",
      "source_cells": [
        {"file": "toy.csv", "sha256": "REPLACE_WITH_TOY_CSV_SHA256", "row": 2, "column": "value", "raw_value": "1.20", "unit": "u"}
      ],
      "values": [{"cell": 0, "value": 1.20, "unit": "u"}],
      "marks": [{"cell": 0, "encoded_value": 1.20, "unit": "u", "color": "#4477AA", "marker": "circle"}],
      "legend": {"label": "Toy A", "color": "#4477AA", "marker": "circle"},
      "style": {"color": "#4477AA", "marker": "circle", "opacity": 0.8}
    },
    {
      "id": "B", "unit": "u",
      "source_cells": [
        {"file": "toy.csv", "sha256": "REPLACE_WITH_TOY_CSV_SHA256", "row": 3, "column": "value", "raw_value": "0", "unit": "u"}
      ],
      "values": [{"cell": 0, "value": 0, "unit": "u"}],
      "marks": [{"cell": 0, "encoded_value": 0, "unit": "u", "color": "#EE6677", "marker": "square"}],
      "legend": {"label": "Toy B", "color": "#EE6677", "marker": "square"},
      "style": {"color": "#EE6677", "marker": "square", "opacity": 0.8}
    }
  ],
  "elements": [],
  "legend": [
    {"series": "A", "label": "Toy A", "color": "#4477AA", "marker": "circle"},
    {"series": "B", "label": "Toy B", "color": "#EE6677", "marker": "square"}
  ],
  "style": {"series": {
    "A": {"color": "#4477AA", "marker": "circle", "opacity": 0.8},
    "B": {"color": "#EE6677", "marker": "square", "opacity": 0.8}
  }}
}
```

After any source-data edit, regenerate both the affected plotted marks and the map's changed hashes/raw values and dependent encodings before rerunning the command. Updating only `raw_value` expectations is not a redraw.

## Contract handling

A contract may be JSON Schema (`properties`/`required`), a `fields` list/map, a list of field names/objects, or a plain mapping of original field names. The helper checks discoverable keys without flattening nested schema. The agent must read descriptive requirements that cannot be validated mechanically and use exact nested types. If no recognized machine-readable contract exists, use task.md's explicit requirements and document the ambiguity. The helper injects only the original `case_id`, and refuses an existing conflicting value.
