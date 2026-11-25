---
name: source-bound-scientific-diagrams
description: Generate and edit scientific relationship schematics, mechanisms, workflows, and source-data charts with editable SVG, real PNG/PDF exports, element provenance, source-preserving revisions, and deterministic independent per-element source traceability reverse-checks.
---

# Source-bound scientific diagrams — v2.0.0

Turn the ACTUAL case materials into scientifically correct, editable artwork. This is an execution skill, not a set of answers. The fixed cases, scientific content, output field names, and export specifications are unknown until runtime. Read them; never infer them from filenames or domain labels. Do not use image generation for scientific relationships or rasterize editable text into a background.

## Start here (first 2–4 tool calls)

1. Read `/input/case.json`, the actual `task.md` (find its location), and `environment/resources.yaml` (locate if necessary). Inventory input attachments and tool versions. The installed skill is `/skills/weekly-skill`; resolve script paths from that directory, not the current working directory.
2. Make `/app/work` and `/app/output`. Run:
   `python3 /skills/weekly-skill/scripts/diagram.py inspect --input /input --out /app/work/input_inventory.json`
   Read `output_contract` in full, including nested structure, required formats, filenames and language. Create an honest initial `/app/output/result.json` with the original `case_id`, all required fields, `status: partial`, and precise unfinished work, using required field types. Save useful draft artifacts early; do not spend the entire budget on analysis.
3. Read actual source contents. For PDFs: `pdftotext -layout` or PyMuPDF page text; render relevant original pages and examine captions, legends and figure panels. If text is empty or garbled, render/OCR the relevant pages. For biology, use primary source passages and original figure/caption, not general domain memory. For data, read raw CSV/XLSX values, header, units, ordering, categories and missing values. For source SVG, inspect XML, IDs, groups, text, paths, transforms, viewBox, styles and linked assets AND render the original before editing. PPTX/Office/drawio inputs require their native source preserved and real rendered previews.
4. Decide **create versus edit** from the workorder. For an edit, preserve the actual supplied source; a newly drawn approximation is not a source-preserving edit. Read [references/method.md](references/method.md) for the relevant workflow and [references/interface.md](references/interface.md) for helper interfaces and a clearly synthetic example.

## Scientific model before drawing

Write `/app/work/figure_spec.json` (or a richer equivalent) containing source IDs, entities, edges, compartments, data mappings, and export constraints. Write `/app/output/source_map.json`: each authored node/entity, edge, group, and explicitly source-bound data mark/legend ID → actual input path + SHA256 + page/table/row/figure/panel/line/cell locator + supporting passage/value (or explicit `not_applicable` only for pure geometry) + nonempty interpretation and relationship status. Use the preferred schema in [references/interface.md](references/interface.md). The source quote must be read from the actual material. Include source and output versions. Record unknown/uncertain interpretations explicitly; unconfirmed human review is `not_performed`, never 'approved'. Immediately reverse-check coverage with `source_audit.py`; repair all missing entries, hashes, locators, evidence or quote matches before continuing. This authoring-time audit is mandatory, not optional provenance decoration.

- Give each distinct scientific entity a stable ID; retain exact names, symbols, species, quantities and units. Never invent a gene, reaction, concentration, time point, or causal mechanism.
- Model edge `source`, `target`, `kind`, sign, direction and provenance separately. Activation: arrowhead at target; inhibition: **T-bar at target**; association: undirected; containment: enclosing compartment; temporal sequence: arrow or numbered steps. Do not convert correlation into causation, indirect into direct, or bidirectional into one-way. Two incompatible passages become a documented conflict, not a confident composite mechanism.
- Check compartment placement, upstream/downstream order, panel correspondence, conditions, controls and which relation applies under which condition. Scientific correctness takes priority over pretty layout.
- Each data category gets one stable legend entry with the exact same label, color, shape and order as marks. Use actual source data, explicit axes/scales/units; distinguish zero from missing. Recompute visual mappings after data changes. No invented statistical tests, error bars, counts or p-values. Do not replace a requested chart with a generic flowchart.

## Produce actual editable deliverables

Use the renderer that fits the task: SVG XML/native drawing code for mechanisms; native source editing for revisions; matplotlib for actual data charts (set `svg.fonttype='none'`, `pdf.fonttype=42`); native PPTX/drawio if explicitly required. You may use or adapt the supplied helper for ordinary node-edge layouts; it is OPTIONAL and is not a scientific extractor. Custom code is preferable when complex biology, faithful source layout, multiple panels or chart requirements exceed it.

For SVG keep separate named groups `compartments`, `edges`, `entities`, `labels`, `legend`, with stable element IDs, selectable `<text>` elements, and sensible `viewBox`/physical dimensions. Labels need not be outlined; choose an installed font supporting the actual script, Greek and symbols (`fc-match`/`fc-list`), record substitutions. Fit at FINAL print size (normally 7–10 pt if unconstrained), readable stroke widths, high contrast, no overlap or clipping, colorblind-conscious color plus shape/style redundancy. Only use dimensions/DPI defaults if unspecified, and disclose that choice.

Export **real SVG, PNG and PDF** for the concrete workorder, plus any explicitly requested EPS/TIFF/native source. Do not rename a file extension. Use Inkscape, CairoSVG or a provided converter; actual preview/export files must exist, open and contain the rendered content. At 300 DPI, raster width = round(mm / 25.4 * 300); use the task's DPI if different. Respect requested page size, transparency/background and color mode. RGB is not CMYK; if CMYK is required use a real color-managed conversion and verify it. If unavailable, retain valid RGB drafts, report partial and the exact unmet requirement. For PDF check actual page box and fonts (`pdfinfo`, `pdffonts`); for PNG/TIFF check real pixels, DPI metadata and mode with Pillow. Do not claim fonts embedded based on SVG declarations.

Typical helper calls (use actual filenames):
```
python3 /skills/weekly-skill/scripts/diagram.py render --spec /app/work/figure_spec.json --out /app/output/figure.svg
python3 /skills/weekly-skill/scripts/source_audit.py --spec /app/work/figure_spec.json --map /app/output/source_map.json --out /app/output/source_checks.json --svg /app/output/figure.svg
python3 /skills/weekly-skill/scripts/diagram.py export --svg /app/output/figure.svg --dpi 300 --out /app/output/export_checks.json
python3 /skills/weekly-skill/scripts/diagram.py audit --svg /app/output/figure.svg --out /app/output/svg_checks.json
```
The helper reports unavailable/failed exports honestly. It does not replace visual or scientific review.

## Edit without destroying the source

Keep an untouched original copy and hash; make an editable revised copy. Map requested changes to stable source IDs and modify only those elements, connected geometry and dependent legends/data. Preserve unaffected entities, scientific meanings, panels, layer structure, IDs and transforms. For the helper's conservative SVG text/style edit:
```
python3 /skills/weekly-skill/scripts/diagram.py patch --svg INPUT.svg --changes /app/work/changes.json --out /app/output/revised.svg
```
For geometry/complex edits, use source-aware custom code. Do not embed the original as a bitmap and overlay labels as a substitute for editing it. Do not globally replace a string that also appears in unrelated entities. Save element-level before/after records, source hash, new hash, reason and affected downstream mappings. If only raster source exists, preserve it as a reference, build an editable reconstruction and explicitly label the limit; do not claim layer preservation. Produce before/after previews and a comparison of changed/unchanged elements.

## Verify and close the loop

1. Re-read scientific model against actual sources. Compare every requested node, edge, sign, arrow target, grouping, number and unit; check forbidden unsupported additions. Compare with supplied original figure visually when present. A similarity score alone proves neither mechanism correctness nor source preservation. **Mandatory final reverse-check:** rerun `source_audit.py` with the final spec, map and rendered SVG, retain `/app/output/source_checks.json`, and treat its nonzero exit as a failed mechanical check that blocks a traceable-complete claim. `scientific_review` remains `not_performed`: matching quotes/hashes and SVG IDs do not certify scientific correctness.
2. Render final PNG, then inspect it with available image viewing tools. If no image viewer, use pixel bounding boxes/text metrics and explicitly record visual inspection unavailable. Inspect at final print size; repair label overflow, collisions, covered arrowheads, clipping, confusing crossings and missing legend units. Audit script warnings require review, not automatic acceptance.
3. Record each export's actual file, SHA256, format signature, measured dimensions, mode, DPI and tool/version. Distinguish measured, manually inspected, unknown, not applicable and failed. Retain commands and actual errors in `/app/output/run.log`; inspect PDF as well as PNG. At least one render-repair iteration if problems are found; stop when constraints pass or budget requires an honest partial.
4. Deliver `/app/output/result.json` with **every original `output_contract` field at its original name and required nesting/type**, plus exact original `case_id`. Fill it from actual artifacts and findings, not the example. Include editable source paths, exports, sources, changes, uncertainties, runtime/checks and honest status (use contract enum). Required paths must point to files in `/app/output` that exist. Do not hide required fields solely inside `main_result` or rename Chinese keys to English. Supplementary details may live in sidecar JSON/Markdown linked from those fields.
5. You can validate a fully authored report with:
   `python3 /skills/weekly-skill/scripts/diagram.py finalize --case /input/case.json --report /app/work/report.json --out /app/output/result.json`
   This verifies contract field presence/types when discoverable and preserves `case_id`; it does NOT fill scientific answers or certify success. Inspect errors and correct the report. Do not overwrite valid partial deliverables with an empty error response.
6. Final response briefly names deliverables and remaining limitations. Do not fabricate comparison scores, human confirmation, tool success, hidden cases, software state, or baseline gains. Platform runs its own baseline comparisons.

## Failure handling and budget

Budget is 900 seconds and 64 model requests. Target first editable draft by minute 4, exports by minute 8, then scientific/visual checks and contract completion. Reserve the final 2 minutes for writing actual results. Missing material → identify the exact missing file/passage and preserve verifiable partial work. Contradiction → show alternatives in uncertainty and avoid unsupported edge. Missing font → use a tested substitute and record it. Converter failure → try one available alternative, keep SVG, record actual failure, and mark unmet export partial. Invalid source → preserve original and report parse error. Never equate no warnings with scientific validation. Re-run only after relevant edits; do not install large toolchains or loop endlessly.

## Resources and boundaries

Python 3.8+ standard library powers inspect, patch, render, SVG audit, independent per-element source reverse-checks and contract checks. Export tries installed Inkscape, `rsvg-convert`, then optional CairoSVG. Optional Pillow inspects rasters; `jsonschema` checks actual JSON schemas; Poppler checks PDFs/fonts. Prefer environment-provided tools; if missing and installation is allowed: `python3 -m pip install cairosvg pillow jsonschema` (CairoSVG also needs system Cairo). No network or API key is needed by this skill. No packaged scientific answers or fixed-case outputs. Version 2.0.0; source code and references are maintained together. Scope: scientific diagram/editing and source-data mapping, not literature review, statistical inference or decorative illustration.
