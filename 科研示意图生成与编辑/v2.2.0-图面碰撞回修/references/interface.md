# Helper interfaces and synthetic example

`diagram.py` is a deterministic file/render helper. Scientific extraction, layout decisions and final source judgement belong to the executing agent. All output is generated from runtime inputs; the helper contains no biological content.

## Commands

- `inspect --input DIR --out JSON`: relative paths, sizes, hashes, optional tool discovery. Reads files, never guesses science from filenames.
- `render --spec JSON --out SVG`: draw explicitly positioned compartments, nodes, edges and legend with selectable text. Supports arrow, activation, inhibition, association and sequence. `points` overrides routing. Unsupported relations are rejected. Use custom drawing code for other semantics.
- `patch --svg FILE --changes JSON --out SVG`: conservative ID-based attribute/text edits. Refuses duplicate/missing IDs, complex text replacement and unknown patch operations. Writes `OUT.changes.json` with old/new values and hashes; original untouched. Geometry edits require custom code and independent checks.
- `export --svg SVG --dpi NUMBER --out JSON`: try installed exporters; produce same-stem PNG/PDF. Report actual errors and whether files exist. Pillow (if present) records PNG actual size/mode/DPI; pdfinfo/pdffonts record actual PDF measurements. Failure does not delete the SVG.
- `audit --svg SVG --out JSON`: parse SVG, inventory text/group/IDs; warn on raster references, external images, absent text, duplicate IDs, viewBox problems. Does not certify scientific correctness or guarantee collision-free geometry.
- `scripts/layout_audit.py --svg SVG --out JSON`: standalone Python 3.8+ stdlib geometric audit. Analyze SVG text/tspan positions, inherited/basic styles and transforms, viewBox overflow, text-text collisions, and line/polyline/path connector intersections. Text boxes use the disclosed deterministic Unicode metric in the report, not actual font shaping. Unsupported cases are marked `needs_visual_review`.
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

## Geometric layout audit (SYNTHETIC INPUT ONLY)

The following invented, non-scientific SVG demonstrates only the input mechanics; it is not a case answer or included test artifact. Save it as `/tmp/layout-demo.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 90">
  <g font-family="sans-serif" font-size="16">
    <text id="left-label" x="20" y="30">Left</text>
    <text id="right-label" x="160" y="30">Right</text>
  </g>
  <polyline id="connector" points="20,65 220,65" fill="none" stroke="black"/>
</svg>
```

Run:
```bash
python3 scripts/layout_audit.py --svg /tmp/layout-demo.svg --out /tmp/layout_checks.json
```

Exit `0` means no modeled mechanical issue was found; exit `1` means the report contains collision/overflow findings that require SVG repair, rerendering and re-audit; exit `2` reports an input or audit error. The JSON is written for successful and failed audits and includes element IDs/references, estimated or derived boxes, severity, scope, the exact estimation rules, and `needs_visual_review` reasons. IDs absent from the source are explicit generated locators. **Every exit status still requires final actual rendered visual inspection; this audit never certifies scientific correctness.** Review rotated/path text, custom SVG fonts, and other unsupported geometry rather than treating those omissions as passes.

## Contract handling

A contract may be JSON Schema (`properties`/`required`), a `fields` list/map, a list of field names/objects, or a plain mapping of original field names. The helper checks discoverable keys without flattening nested schema. The agent must read descriptive requirements that cannot be validated mechanically and use exact nested types. If no recognized machine-readable contract exists, use task.md's explicit requirements and document the ambiguity. The helper injects only the original `case_id`, and refuses an existing conflicting value.
