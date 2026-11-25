# Helper interfaces and synthetic example

`diagram.py` is a deterministic file/render helper. Scientific extraction, layout decisions and final source judgement belong to the executing agent. All output is generated from runtime inputs; the helper contains no biological content.

## Commands

- `inspect --input DIR --out JSON`: relative paths, sizes, hashes, optional tool discovery. Reads files, never guesses science from filenames.
- `render --spec JSON --out SVG`: draw explicitly positioned compartments, nodes, edges and legend with selectable text. Supports arrow, activation, inhibition, association and sequence. `points` overrides routing. Unsupported relations are rejected. Use custom drawing code for other semantics.
- `patch --svg FILE --changes JSON --out SVG`: conservative ID-based attribute/text edits. Refuses duplicate/missing IDs, complex text replacement and unknown patch operations. Writes `OUT.changes.json` with old/new values and hashes; original untouched. Geometry edits require custom code and independent checks.
- `scripts/edit_audit.py --before ORIGINAL.svg --after REVISED.svg --changes REVISED.svg.changes.json --out edit_checks.json`: mechanically compare parsed SVG XML per stable ID. Tags, namespaced attributes (including href/style/geometry), and ordered text/tspan content are digested independently of raw formatting. Original IDs must remain present and unique; actual changed/added IDs must exactly match the declarations, and `input_sha256` must match the original. Writes per-ID before/after digests/statuses and flags embedded or linked revised images with local-relative existence measurements. No network fetching; native Office and semantic correctness are not covered. Failure exits nonzero and must be fixed before exports.
- `export --svg SVG --dpi NUMBER --out JSON`: try installed exporters; produce same-stem PNG/PDF. Report actual errors and whether files exist. Pillow (if present) records PNG actual size/mode/DPI; pdfinfo/pdffonts record actual PDF measurements. Failure does not delete the SVG.
- `audit --svg SVG --out JSON`: parse SVG, inventory text/group/IDs; warn on raster references, external images, absent text, duplicate IDs, viewBox problems. Does not certify scientific correctness or guarantee collision-free geometry.
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

## Native-SVG source edit audit

Run immediately after every helper patch or custom SVG edit, before any export:

```
python3 scripts/edit_audit.py --before original.svg --after revised.svg --changes revised.svg.changes.json --out edit_checks.json
```

The change file may be the helper-produced object with a `changes` list (recommended) or a bare list of objects containing `id`. A bare list can be parsed, but cannot pass the required original-hash check unless the hash is supplied in the helper-compatible object form. The auditor never writes either SVG and refuses an output path that aliases an input. Duplicate or missing original IDs, undeclared actual changes/additions, declared IDs that do not differ, and a wrong/missing `input_sha256` fail the audit. Revised `<image>` references are warnings with separate embedded/raster/external classifications and measured local-relative `exists`/`is_file`; missing links do not silently count as resolved assets.

**Synthetic changed/unchanged example (not a scientific case):** original and revised differ only in `sample-label`:

```xml
<!-- original.svg -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 80">
  <g id="sample"><rect id="sample-shape" width="180" height="60"/><text id="sample-label">Before</text></g>
</svg>
<!-- revised.svg: identical except the text below -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 80">
  <g id="sample"><rect id="sample-shape" width="180" height="60"/><text id="sample-label">After</text></g>
</svg>
```

Use a change log whose `input_sha256` is the actual SHA256 of `original.svg` and whose only declaration is `{"id":"sample-label","op":"text","value":"After"}`. With the command above, `sample-label` is `changed`, while `sample-shape` and its identified parent `sample` are `unchanged`; only the declared text ID is listed as actually different. Editing `sample-shape` without declaring it, removing it, or changing the logged hash makes the audit fail. The JSON records before/after digest and status for every ID. This mechanical result does not certify scientific or visual correctness, and objects without IDs cannot independently prove preservation.

## Contract handling

A contract may be JSON Schema (`properties`/`required`), a `fields` list/map, a list of field names/objects, or a plain mapping of original field names. The helper checks discoverable keys without flattening nested schema. The agent must read descriptive requirements that cannot be validated mechanically and use exact nested types. If no recognized machine-readable contract exists, use task.md's explicit requirements and document the ambiguity. The helper injects only the original `case_id`, and refuses an existing conflicting value.
