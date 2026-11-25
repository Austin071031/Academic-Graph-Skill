# Tool interfaces, formats and synthetic demonstration

All code is input-driven. No formal case content or pre-rendered answer is included. Python 3.8+ standard library supports model render/validation, hashing, native SVG patches, local XML diff and contract presence/type checks. Exporters are discovered at runtime. Prefer provided Inkscape/rsvg-convert; optional CairoSVG needs system Cairo, Pillow measures actual PNG, PyMuPDF checks PDF page text, jsonschema checks supplied JSON Schema. No network or credentials are needed by the skill.

## Model schema

`pathway.py` consumes one authored JSON object. It does NOT extract biological relations from text. Required:

- `width,height`: positive finite viewBox coordinates. Physical `width_mm,height_mm` default to 180 mm and matching aspect ratio; use actual workorder constraints. `font_size` defaults to 16 viewBox units: physical points = font_size × width_mm / width × 72 / 25.4. Pick values for readable final print, not just screen size.
- `nodes`: list of `id,label,type,x,y,w,h`; positive sizes, stable XML-safe IDs. Types: gene, protein, complex, family, receptor, metabolite, cell, phenotype, process, unknown. Optional `compartment,evidence,value,data_ref,fill,italic`. Gene italic defaults true, but should be overridden for actual species/source convention. `value:null` is missing, not zero.
- `compartments`: optional `id,label,x,y,w,h,kind,fill,stroke,evidence`. `label_x,label_y,label_anchor` can move region labels clear of members. `kind:membrane` creates a band; receptor nodes assigned there must intersect it. Other nodes assigned to a region must be contained. Use nesting or separate cells as justified by source. Overlapping node boxes are warnings to review.
- `edges`: list of `id,source,target,kind,evidence`. Kinds: activation, inhibition, binding, association, phosphorylation, dephosphorylation, ubiquitination, modification, recruitment, transport, transcription, translation, sequence, unknown. Specific processes require `label`. Optional `indirect,uncertain,bidirectional,points,label_x,label_y`. Binding/association/unknown have no arrow. Inhibition has a T-bar at target. Marker tips are offset slightly outside the target border so node fills cannot obscure them. Other kinds have a target arrow, differentiated by explicit process labels. Indirect/uncertain/unknown edges are dashed with legend explanation.
- `points`: optional polyline `[[x,y],...]`, including actual source and target boundaries. Necessary for self-loops, feedback, obstacle avoidance, parallel edges and deliberate multi-compartment routes. Straight default routes are not a topology algorithm. Receptor shape is a schematic labeled box intersecting membrane, not a claimed biomolecular structure; custom drawing can improve source fidelity.
- `evidence`: map of runtime evidence IDs to `{path,sha256,locator,quote,page?}`. `page` is 1-based for PDF. Plain-text quote checks normalize whitespace; PDF checks use actual specified page if PyMuPDF is installed. Unsupported file types and visual-only evidence need Agent review. A missing quote is a warning, not fabricated evidence. Reference IDs are attached to each node/edge/compartment's `evidence` list.
- `encoding` optional: categorical `{mode:"categorical",label,categories:{category:color},missing_color?}` or continuous `{mode:"continuous",label,domain:[min,max],colors:[hex,...],missing_color?}`. Continuous colors must be at least two six-digit hex colors; piecewise interpolation uses the same code for glyphs and legend. Supply three colors and symmetric domain for a justified zero-centered scale. Categorical lookup uses string keys. `legend_x,legend_y` can place the encoding legend.
- `data_ref` optional per node: actual raw-data cell `{path,sha256,row,column,delimiter?}` for CSV/TSV, with row **1-based excluding header**; or `{path,sha256,keys:[...]}` for JSON, keys/indices traversing the actual document. JSON numeric indices are zero-based. `check` compares node `value` to independently reloaded raw cell, with tight numeric tolerance, not merely the rendered model's duplicate data. Missing cells remain explicit.
- `font_family,title,background,legend_x,legend_y,relation_labels` optional. Relation legend is automatically generated from actual edge type/directness/uncertainty/direction styles. Type-shape semantics and any other visual encodings need explicit native legend additions if required; do not omit a required legend because the helper lacks it. Prefer custom SVG additions or a source-aware renderer over misrepresenting semantics.

Keep provenance/labels source-bound. Do not use arbitrary fill alongside an active encoding to override mapped values. The encoding takes precedence. Edges use neutral fixed width/color so they do not invent quantitative evidence. Newlines produce selectable tspans; there is no automatic text wrapping. Inspect actual renders for fit, fonts and overlap. Negative/invalid geometry and relation IDs are rejected. Warnings require review.

## Minimal invocation — synthetic example ONLY

This toy describes invented generic input/output objects, not an official biological example. It demonstrates the complete interface; no generated demonstration files are shipped as answers. Run in a scratch directory, not the official output directory:

```sh
mkdir -p /app/work/demo
cd /app/work/demo
python3 - <<'PY'
import hashlib,json,pathlib
p=pathlib.Path('synthetic.txt').resolve()
p.write_text('SYNTHETIC EXAMPLE ONLY. Example input activates example output.\n')
spec={
 'width':900,'height':450,'width_mm':180,'height_mm':90,'font_size':20,
 'title':'Synthetic interface demonstration',
 'compartments':[],
 'nodes':[
  {'id':'example-input','label':'Example input','type':'protein','x':90,'y':120,'w':220,'h':70,'evidence':['toy']},
  {'id':'example-output','label':'Example output','type':'protein','x':570,'y':120,'w':220,'h':70,'evidence':['toy']}],
 'edges':[{'id':'example-effect','source':'example-input','target':'example-output','kind':'activation','evidence':['toy']}],
 'legend_x':90,'legend_y':350,
 'evidence':{'toy':{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'locator':'line 1, synthetic only','quote':'Example input activates example output.'}}
}
pathlib.Path('figure_spec.json').write_text(json.dumps(spec))
PY
python3 /skills/weekly-skill/scripts/pathway.py render --spec figure_spec.json --out example.svg
python3 /skills/weekly-skill/scripts/pathway.py check --spec figure_spec.json --svg example.svg --out checks.json
python3 /skills/weekly-skill/scripts/diagram.py export --svg example.svg --dpi 300 --out export_checks.json
```

Illustrative output: editable `example.svg` with 5 named layers, two selectable labels, target arrow and matching relation legend; `checks.json` describes actual mechanical checks and leaves science to Agent review; `example.png`/`example.pdf` and measured export checks exist only if conversion succeeds. Expected 180×90 mm at 300 DPI is approximately 2126×1063 pixels and 510.24×255.12 PDF points. This is illustrative interface behavior, NOT a prepared official `result.json`. At runtime `result.json` must follow the original case's actual contract, not this example.

## Commands

```
pathway.py render --spec JSON --out SVG
pathway.py check --spec JSON [--svg SVG] --out JSON
pathway.py diff --before ORIGINAL.svg --after REVISED.svg [--allowed IDS.json] --out JSON

diagram.py inspect --input DIR --out JSON
diagram.py patch --svg INPUT.svg --changes JSON --out REVISED.svg
diagram.py export --svg SVG --dpi NUMBER --out JSON
diagram.py audit --svg SVG --out JSON
diagram.py finalize --case JSON --report JSON --out JSON
```

`check` writes mechanical failures then exits nonzero. An input parse failure can instead return an error on stderr; retain useful prior artifacts. Check source hashes, exact quote locations, raw values, ID coverage, label/geometry/fill metadata, target-marker definitions, edge route/directness, compartment containment and straight/routed edge intersections. It does not validate all drawn geometry, complex SVG inheritance/transform behavior, complete legend/shape semantics or biological truth. Use independent judgement and render inspection. It is intended for `pathway.py` output IDs; do not redraw source-preserving edits to satisfy it.

`diff` receives a JSON list of exact IDs permitted to change/add/remove. It reports unexpected changes, unchanged count, root-local changes and hashes. ID-based local comparison includes anonymous child content and child ID order. Parents containing an ID-addressed child do not become false positives just because that child's text changed. It is conservative about source serialization and cannot prove CSS/render equivalence; inspect every warning and before/after image. Add expected dependent changes to the allowed list only when actually justified by the edit request.

`patch` example, synthetic only:

```json
[{"id":"example-input-label","op":"text","value":"Revised example input"},
 {"id":"example-input-shape","op":"attrs","value":{"fill":"#CCE4DD"}}]
```

This targets actual IDs, not label substrings. `attrs` cannot change IDs or introduce event handlers. Simple text or a single plain tspan is supported; multiline/styled text requires source-aware per-tspan edits. The patch output must differ from input, and a hash/before-after sidecar is written. The tool does not adjust dependent geometry automatically. For complex native sources preserve IDs and use the appropriate actual XML/object model.

`export` tries provided converters, validates PNG/PDF signatures, writes requested PNG DPI metadata if Pillow is available and reports actual raster dimensions/mode. It records pdfinfo/pdffonts output where installed. Inspect return status in the sidecar; success of the wrapper command is not success of every export. The default output names share the SVG stem. Keep requested dimensions in physical SVG units and avoid tight-bbox cropping. CMYK/other formats require actual conversion beyond this helper. Do not report unmeasured properties as passed.

`finalize` preserves original case_id and validates supported contract forms: JSON Schema, fields lists/maps, plain original-key maps and lists of named descriptors. It can enforce nested JSON Schema when jsonschema is available; descriptive prose contracts require Agent reading. It never fills missing scientific answers or judges completeness. Required final artifact paths and contract-specific enums still need actual checking. It writes atomically and refuses conflicting IDs/type/missing-field errors.
