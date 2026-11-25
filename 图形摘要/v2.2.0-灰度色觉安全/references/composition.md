# Composition interface, constraints and synthetic example

Version 1.3.0. All helpers operate on runtime inputs. The installed directory is `/skills/weekly-skill`; no author machine paths or credentials are required. This compositor is for NEW graphical abstracts. For requested edits, preserve supplied native source; do not recompose it merely to use these tools.

## Runtime artifacts

Keep the original source files immutable. Store authored component specs and their editable SVGs/maps under `/app/output/components/<component-id>/`. This avoids helpers overwriting the top-level source_map.json or export_checks.json. Top-level figure_spec.json is the authored page composition; source_map.json consolidates narrative, element evidence and component source maps. The compositor also writes `figure.svg.composition.json` with exact component hashes, panel roles, source-ID → composed-ID maps and placements. Link this from the original contract's provenance fields.

```sh
python3 /skills/weekly-skill/scripts/abstract.py render --spec /app/output/figure_spec.json --out /app/output/figure.svg
python3 /skills/weekly-skill/scripts/abstract.py check --spec /app/output/figure_spec.json --svg /app/output/figure.svg --out /app/output/composition_checks.json
python3 /skills/weekly-skill/scripts/diagram.py export --svg /app/output/figure.svg --dpi 300 --out /app/output/export_checks.json
```

Check returns nonzero for actual evidence/hash/quote/data/model errors. Warnings require review and explicit resolution; they are not proof of failure or success. An unexpected exception may leave existing artifacts untouched: do not report stale previews as newly exported.

## Page specification

Required dimensions `width,height,width_mm,height_mm` must be positive finite numbers, with identical viewBox/physical aspect ratios. `title` is source-supported, concise and selectable. Optional `font_size` (viewBox units, default 20), `font_family`, `background`, `legend` (explicit textual key), `legend_y`. The rule for converting viewBox font size to physical points is `size × width_mm / width × 72/25.4`. Scale component labels too; a 9 pt chart shrunk to half-width is approximately 4.5 pt and needs a larger original font.

`panels` is an ordered list, each with:

- `id`: unique XML-safe stable semantic ID; do not begin with reserved `ga-`. `x,y,w,h`: explicit viewBox rectangle entirely on canvas. Pick geometry from workorder/narrative, not an arbitrary grid. Panels should not overlap each other, the title, or the footer legend.
- `roles`: list drawn from `question,methods,results,conclusion`. Several roles can share a panel; a conclusion can be a bold results takeaway. Coverage warnings are meaningful, but do not override a restricted source edit request.
- `title`, optional `body,takeaway`: supported concise visible text. `body` appears above the visual, `takeaway` beneath it. Text wraps heuristically; inspect actual rendered widths. Retain scientific symbols and exact names. Do not add a long explanation where a visual should be.
- `asset`: actual editable component SVG path (absolute or relative to the spec). Native paths/shapes/text/defs/markers/clips/use are imported, retaining inherited root text/paint presentation attributes, inline styles and exact viewBox. Imported IDs and references are prefixed `<panel-id>--asset-`, with an explicit mapping sidecar. The original component is retained unchanged. This is vector composition, not screenshot embedding.
- `evidence`: runtime evidence ID list for the panel claim. `elements`: list of `{id,evidence,value?,data_ref?}` where id is an actual original component SVG ID. This list maps key entities, relations, data marks, legends and annotations to evidence; panel-level citations alone are not sufficient. For a chart, retain the component source_map.json and map composed IDs using the prefix; record individual marker/cell indices where needed.
- `accent`: optional categorical design color; it has no numerical meaning unless explicitly mapped and labeled.

`evidence` at page root maps IDs to `{path,sha256,locator,quote?,page?}`. Paths refer to actual runtime original files. PDF `page` is 1-based and required for quote checks. For visual-only evidence retain figure/panel coordinates and an honest Agent visual review; no invented quote. The helper checks literal existence, not semantics. Key claims still require Agent judgement.

`data_ref` in `elements` uses `{path,sha256,row,column}` for CSV/TSV, with **1-based data row excluding header**; JSON uses `{path,sha256,keys:[...]}`. Chart helper source_map rows instead include header (first data row=2); keep these two conventions distinct. Direct values are checked independently against the original raw cell. Derived values require recorded formula, operands, units and an independent recomputation; do not mislabel a raw-cell check as derived-value verification.

Assets require a valid explicit viewBox and unique IDs. External linked assets, scripts, raster images and foreignObject are rejected. Complex CSS must be resolved to inline native styles using a source-aware routine first. The standard Matplotlib universal stroke-linejoin/linecap rule is supported. Do not flatten scientific text to paths to bypass this limitation. Supplied SVG with advanced CSS/native features can instead be edited and exported directly without this compositor. Physical crop/clip behavior and transform inherited styles need real preview review.

The page checker independently recomposes from the actual current component bytes/spec and compares with the submitted SVG, verifies mapped SVG IDs and raw evidence/value hashes, and reports missing narrative roles, panel overlaps, coarse wrapping limits, main font size and approximate minimum imported text size after panel scaling. Font estimates do not account for every nested transform or CSS shorthand; inspect real previews. It does NOT validate scientific truth, all glyph bounds/label collisions, arbitrary native semantics or font embedding. Do not revise an original source just to satisfy its canonical recomposition test.

## Minimal invocation — SYNTHETIC interface demonstration only

The following input describes an invented generic workflow solely to demonstrate an interface. No generated answer artifacts are bundled. At execution create this only under a separate scratch demonstration directory, never as official case output:

```sh
mkdir -p /app/work/demo
cd /app/work/demo
python3 - <<'PY'
import hashlib,json,pathlib
p=pathlib.Path('synthetic.txt').resolve()
p.write_text('SYNTHETIC EXAMPLE ONLY. Question: can a demo input reach a demo output? Method: route input to output. Result: routing is observed. Conclusion: the illustrated route works in this toy example.\n')
svg=pathlib.Path('route.svg')
svg.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 220"><defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10Z"/></marker></defs><path id="route" d="M120,110 H340" stroke="#0072B2" stroke-width="3" marker-end="url(#arrow)"/><rect id="input" x="20" y="75" width="110" height="70" fill="#E4F0F6"/><rect id="output" x="350" y="75" width="110" height="70" fill="#E4F0F6"/><text id="input-label" x="38" y="116" font-size="26">Input</text><text id="output-label" x="360" y="116" font-size="26">Output</text></svg>')
panels=[
 {'id':'question','x':28,'y':80,'w':380,'h':180,'roles':['question'],'title':'Toy question','body':'Can a demo input reach a demo output?'},
 {'id':'workflow','x':440,'y':80,'w':732,'h':330,'roles':['methods','results'],'title':'Toy method and observed result','asset':'route.svg'},
 {'id':'takeaway','x':28,'y':285,'w':380,'h':180,'roles':['conclusion'],'title':'Toy conclusion','body':'The route works only in this toy example.'}]
for panel in panels:panel['evidence']=['toy']
panels[1]['elements']=[{'id':v,'evidence':['toy']} for v in ['input','output','route']]
spec={'width':1200,'height':550,'width_mm':180,'height_mm':82.5,'font_size':24,
 'title':'Synthetic interface demonstration ONLY','panels':panels,
 'legend':'Arrow: toy workflow sequence; schematic, not to scale.',
 'evidence':{'toy':{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'locator':'synthetic line 1','quote':'Method: route input to output.'}}}
pathlib.Path('figure_spec.json').write_text(json.dumps(spec))
PY
python3 /skills/weekly-skill/scripts/abstract.py render --spec figure_spec.json --out example.svg
python3 /skills/weekly-skill/scripts/abstract.py check --spec figure_spec.json --svg example.svg --out checks.json
python3 /skills/weekly-skill/scripts/diagram.py export --svg example.svg --dpi 300 --out exports.json
```

Illustrative outputs: native editable `example.svg`, `example.svg.composition.json` with prefixed IDs, actual mechanical `checks.json`, and real PNG/PDF only when a converter succeeds. At 180×82.5 mm/300 DPI PNG is approximately 2126×974 px; PDF about 510.24×233.86 pt. This example does not define the official result schema or scientific content. Real result.json must use the case's actual output_contract and case_id.

## Native source editing and maintenance

`diagram.py patch --svg ORIGINAL --changes EDITS.json --out REVISED` accepts `[{"id":"actual-id","op":"text","value":"actual supported replacement"}]` or `op:attrs` with a dictionary. Targets must exist. Original and output paths must differ. Multi-tspan/styled text, changed geometry and dependent annotations require source-aware edits. Preserve supplied formats and styling; compare before/after previews and list justified allowed IDs with `pathway.py diff --before ORIGINAL --after REVISED --allowed IDS.json --out DIFF.json`. XML diff is local and conservative; it is not a complete inherited-style or visual-equality proof.

All helpers are authored reusable resources; no third-party art or fonts are embedded. Optional libraries retain their respective licenses; use runtime installed fonts and supplied materials under their actual conditions. Version 1.0.0 supports new SVG composition, graph/chart components, source-preserving simple SVG edits and contract checks; native PPTX/drawio/Office and unusual graphic conventions need runtime source-aware code. Preserve module/reference interfaces together when maintaining this skill.
