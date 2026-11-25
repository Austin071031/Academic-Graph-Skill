# Helper interfaces and synthetic example

`diagram.py` is a deterministic file/render helper. Scientific extraction, layout decisions and final source judgement belong to the executing agent. All output is generated from runtime inputs; the helper contains no biological content.

## Commands

- `inspect --input DIR --out JSON`: relative paths, sizes, hashes, optional tool discovery. Reads files, never guesses science from filenames.
- `render --spec JSON --out SVG`: draw explicitly positioned compartments, nodes, edges and legend with selectable text. Supports arrow, activation, inhibition, association and sequence. `points` overrides routing. Unsupported relations are rejected. Use custom drawing code for other semantics.
- `patch --svg FILE --changes JSON --out SVG`: conservative ID-based attribute/text edits. Refuses duplicate/missing IDs, complex text replacement and unknown patch operations. Writes `OUT.changes.json` with old/new values and hashes; original untouched. Geometry edits require custom code and independent checks.
- `export --svg SVG --dpi NUMBER --out JSON`: try installed exporters; produce same-stem PNG/PDF. Report actual errors and whether files exist. Pillow (if present) records PNG actual size/mode/DPI; pdfinfo/pdffonts record actual PDF measurements. Failure does not delete the SVG.
- `audit --svg SVG --out JSON`: parse SVG, inventory text/group/IDs; warn on raster references, external images, absent text, duplicate IDs, viewBox problems. Does not certify scientific correctness or guarantee collision-free geometry.
- `structure_audit.py --spec JSON --svg SVG --out JSON [--tolerance NUMBER]`: cross-check authored spec and actual SVG semantic/XML IDs, required layers, selectable text labels, edge endpoints/self-edges, relation marker encoding, connector boundary geometry, and declared enclosure. Custom `points` are supported. Each check carries `status`/`passed`, `actual`, `expected`, and mechanical scope; nonzero means at least one mechanical failure. The JSON report is also written on a caught processing error. Scientific correctness and source-supported edge direction remain `not_performed_by_helper`.
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
python3 scripts/structure_audit.py --spec demo.json --svg /tmp/demo.svg --out /tmp/demo-structure.json
python3 scripts/diagram.py export --svg /tmp/demo.svg --dpi 300 --out /tmp/demo-export.json
```
Illustrative output: SVG with editable `sample` and `review` groups, native text and one directional edge; real PNG/PDF if a converter is installed; export JSON lists measured properties or actual failure. No rendered example files are included in the submission.

Nodes require numeric `x,y,w,h`, positive size and unique IDs. Newline labels produce tspans. Groups have the same rectangle coordinates. Edges attach to rectangular node boundaries by default; for custom routes pass `points: [[x,y],...]` starting and ending at actual boundary. A node may declare intended enclosure with `group`, `compartment`, or `parent` set to a declared group ID; both spec and SVG rectangles are checked for containment. Legend items have `label,color`; use explicit source-derived ordering. This renderer provides a palette, not scientific data mapping: the agent must populate colors consistently from runtime data. It cannot draw a scientifically faithful complex mechanism without an authored spec.

The structural audit uses the renderer conventions (`ID`, `ID-shape`, `ID-label`, `layer-*`, one direct node/group rectangle, and one `polyline`/`line` per edge). It accepts namespace-qualified XML and unitless/`px` numeric serialization; the default geometry tolerance is 0.01 user units. Transformed geometry and path connectors are deliberately reported for conversion or separate review, not silently assumed correct. Marker checks cover direct attributes and inline styles. A failure requires inspecting and correcting spec/layout or recording unresolved semantics, never just accepting the warning.

Patch input example (synthetic):
```json
[{"id":"sample-label","op":"text","value":"Revised example"},
 {"id":"sample-shape","op":"attrs","value":{"fill":"#CCE4DD"}}]
```
The `text` operation works on simple text or one tspan; a multi-line text tree is deliberately refused to avoid discarding styled content. For real source editing use IDs actually present in the original source, not these synthetic IDs.

## Contract handling

A contract may be JSON Schema (`properties`/`required`), a `fields` list/map, a list of field names/objects, or a plain mapping of original field names. The helper checks discoverable keys without flattening nested schema. The agent must read descriptive requirements that cannot be validated mechanically and use exact nested types. If no recognized machine-readable contract exists, use task.md's explicit requirements and document the ambiguity. The helper injects only the original `case_id`, and refuses an existing conflicting value.
