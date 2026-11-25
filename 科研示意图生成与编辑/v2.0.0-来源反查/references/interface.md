# Helper interfaces and synthetic example

`diagram.py` is a deterministic file/render helper. Scientific extraction, layout decisions and final source judgement belong to the executing agent. All output is generated from runtime inputs; the helper contains no biological content.

## Commands

- `inspect --input DIR --out JSON`: relative paths, sizes, hashes, optional tool discovery. Reads files, never guesses science from filenames.
- `render --spec JSON --out SVG`: draw explicitly positioned compartments, nodes, edges and legend with selectable text. Supports arrow, activation, inhibition, association and sequence. `points` overrides routing. Unsupported relations are rejected. Use custom drawing code for other semantics.
- `patch --svg FILE --changes JSON --out SVG`: conservative ID-based attribute/text edits. Refuses duplicate/missing IDs, complex text replacement and unknown patch operations. Writes `OUT.changes.json` with old/new values and hashes; original untouched. Geometry edits require custom code and independent checks.
- `export --svg SVG --dpi NUMBER --out JSON`: try installed exporters; produce same-stem PNG/PDF. Report actual errors and whether files exist. Pillow (if present) records PNG actual size/mode/DPI; pdfinfo/pdffonts record actual PDF measurements. Failure does not delete the SVG.
- `audit --svg SVG --out JSON`: parse SVG, inventory text/group/IDs; warn on raster references, external images, absent text, duplicate IDs, viewBox problems. Does not certify scientific correctness or guarantee collision-free geometry.
- `source_audit.py --spec JSON --map JSON --out JSON [--svg SVG]`: independently hash each declared source and reverse-check every authored node/entity, edge, group and explicitly source-bound data mark/legend. Check locator/evidence/status fields, normalized UTF-8 text quotes and exact rendered XML IDs. Always writes an element-level report for caught failures; any failed mechanical check exits nonzero. Scientific review remains `not_performed`.
- `finalize --case JSON --report JSON --out JSON`: accept authored results, enforce original case_id, check known original output_contract fields, optionally validate actual JSON schema using jsonschema. Missing fields/type errors are fatal; never auto-invent values. Output is atomic.

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

## Source map and deterministic reverse-check

The **preferred schema** is a root `elements` list. Each object has `element_id`, `path`, `sha256`, a structured `locator`, either `quote` or `value`, and nonempty `interpretation` and `status`. For pure geometry only, use `"quote":"not_applicable"` and explain that geometry in `interpretation`. Relative source paths resolve from the map file's directory. `file`/`source_path`/`source.path`, `source_sha256`, `id`, common supporting-passage field names, top-level locator fields, a root list, an `elements` ID-keyed object, and a straightforward root ID-keyed object are accepted for interoperability; new work should use the preferred names below.

All required fields are mechanical requirements, including nonempty `interpretation` and `status`. Use statuses such as `supported`, `uncertain`, `source_unknown` or `conflicting`; declared unknown/uncertain markers are preserved in the element report and counted for review rather than silently treated as support. At least one nonempty `page`, `table`, `row`, `figure`, `panel`, `line` or `cell` locator is required. For UTF-8 text-like files, quote/value matching is an exact substring check after collapsing whitespace. PDFs, binary and unknown-format sources receive `quote_match: needs_text_or_visual_review` when a quote/value is present: their existence, current hash and locator can pass, but their quote cannot mechanically pass. `scientific_review` is always `not_performed`.

The following is a **SYNTHETIC SCHEMA TEMPLATE ONLY**, not case material. Replace every hash placeholder with the current SHA256 of the synthetic `/tmp/demo-source.md`; the four entries correspond to the synthetic render spec above:

```json
{
  "elements": [
    {
      "element_id": "sample",
      "path": "/tmp/demo-source.md",
      "sha256": "REPLACE_WITH_CURRENT_64_HEX_SHA256",
      "locator": {"line": 1},
      "quote": "Example input",
      "interpretation": "Synthetic input node label",
      "status": "supported"
    },
    {
      "element_id": "review",
      "path": "/tmp/demo-source.md",
      "sha256": "REPLACE_WITH_CURRENT_64_HEX_SHA256",
      "locator": {"line": 2},
      "quote": "Example review",
      "interpretation": "Synthetic review node label",
      "status": "supported"
    },
    {
      "element_id": "flow",
      "path": "/tmp/demo-source.md",
      "sha256": "REPLACE_WITH_CURRENT_64_HEX_SHA256",
      "locator": {"line": 3},
      "quote": "Example transfer",
      "interpretation": "Synthetic sequence from sample to review",
      "status": "supported"
    },
    {
      "element_id": "region",
      "path": "/tmp/demo-source.md",
      "sha256": "REPLACE_WITH_CURRENT_64_HEX_SHA256",
      "locator": {"line": 4},
      "quote": "Example region",
      "interpretation": "Synthetic enclosing group",
      "status": "supported"
    }
  ]
}
```

The synthetic source is four lines containing `Example input`, `Example review`, `Example transfer`, and `Example region`. After rendering `/tmp/demo.svg` and saving the completed map as `/tmp/demo-source-map.json`, invoke:

```
python3 scripts/source_audit.py --spec /tmp/demo.json --map /tmp/demo-source-map.json --out /tmp/demo-source-checks.json --svg /tmp/demo.svg
```

`--svg` is optional but, when supplied, every required spec ID must occur as an actual XML `id` attribute; text substring matching is not accepted. Explicitly source-bound `data_marks`/`marks`/`legend`/`legends` items must also have stable IDs and map entries. Unmarked decorative legend entries are not implicitly made source claims. The report contains global checks, per-element checks/status, unmapped and extra IDs, summary counts, and `scientific_review: not_performed`. A pass means only that no mechanical check failed; `needs_review` elements can coexist with an overall mechanical pass.

## Contract handling

A contract may be JSON Schema (`properties`/`required`), a `fields` list/map, a list of field names/objects, or a plain mapping of original field names. The helper checks discoverable keys without flattening nested schema. The agent must read descriptive requirements that cannot be validated mechanically and use exact nested types. If no recognized machine-readable contract exists, use task.md's explicit requirements and document the ambiguity. The helper injects only the original `case_id`, and refuses an existing conflicting value.
