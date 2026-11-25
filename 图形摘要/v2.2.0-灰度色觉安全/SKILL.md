---
name: source-bound-graphical-abstract
description: Creates or source-preservingly edits single-page scientific graphical abstracts from actual papers, records and data. Use for graphical abstract workorders requiring question–methods–results–conclusion storytelling, accurate entities and encodings, editable layered sources, real SVG/PNG/PDF and element-level evidence.
---

# Source-bound graphical abstract — 2.2.0

Produce the actual requested artwork, not just a design plan or evidence report. This skill contains reusable tools and an explicitly synthetic interface demonstration; no official answers. Scientific judgement belongs to the executing Agent: a quote match, export success or clean helper check does not prove scientific correctness.

## Start with the actual contract

Read `/input/case.json`, actual `task.md`, `environment/resources.yaml` (locate if needed), and every relevant attachment. Read the **entire original output_contract**, including original Chinese keys, nesting, field types, status vocabulary, requested figure/panels, revision instructions, dimensions and native file formats. Use actual material over misleading domain labels. Work in `/app/work`; all final artifacts and `/app/output/result.json` belong in `/app/output`. Installed tools are relative to `/skills/weekly-skill`, not cwd.

```sh
python3 /skills/weekly-skill/scripts/diagram.py inspect --input /input --out /app/work/inventory.json
```

Enumerate every requested figure/panel/edit and its required source, native format and exports in the existing source_map or working notes. A named source figure is one work item, not permission to omit other requested figures. Count completed deliverables against that inventory. Save an honest partial `result.json` early, retaining exact case_id and original contract fields/types. Budget: 64 model requests, 900 seconds. Aim for editable first draft by minute 4, real previews by minute 8; reserve final 2 minutes for review and contract completion. If several figures are requested, get a usable source and preview for every figure before polishing any one; apply the time budget to the whole case. Prefer available tools to prolonged installation. Follow supplied constraints over defaults and helper preferences.

## 1. Ground the four-part narrative

Read actual source files, not titles or assumed familiar biology. For PDFs extract with `pdftotext -layout`/PyMuPDF and render relevant original figures, captions and pages. OCR only when needed; visually check Greek, signs, subscripts and units. Record 1-based original PDF pages. Primary biological source materials for the requested figure (including figure03 when applicable) and actual chart data are mandatory evidence. Do not invent a simulation for a drawing workorder.

Build a compact requirement → element → evidence table inside the existing source_map; reuse it during final review rather than creating another mandatory audit ledger. Identify **question, methods, core results, conclusion**. State the actual knowledge gap, study object/conditions, essential intervention/measurement, strongest supported result, and appropriately bounded take-home claim. Distinguish observed association, inferred mechanism and causal intervention. Preserve species, control, dose/time, units and uncertainty. For the main result, identify the exact source-supported contrast: which groups or states differ, the direction, measured value/unit if provided, and applicable conditions. Show that contrast visibly in the actual chart or mechanism, with a concise bounded takeaway; a generic workflow and four role headings alone do not communicate the result. The conclusion cannot be stronger than the source result. Missing data stay missing, never zero or invented statistics.

Choose one visual main message; put supporting detail in a caption/source sidecar rather than shrinking a wall of prose onto the canvas. All four narrative roles must be represented visually or in concise selectable labels on the same page, except when the workorder explicitly restricts the requested edit. Methods must show the actual procedure or mechanism; results must show a source-bound chart, explicit observed contrast, or supported qualitative finding. Four text boxes alone are insufficient.

Save `/app/output/source_map.json` and authored specs: every key entity, edge, number, panel claim, spatial relation and encoding maps to actual input path, SHA256, version, page/figure/panel/paragraph or table cell, supporting passage/value and interpretation. Track ambiguity and visual evidence explicitly. Human confirmation is `not_performed` unless actually obtained.

## 2. Choose creation or source-preserving revision

For a **revision**, first copy/hash/parse/render the supplied native source. Change only requested IDs/objects and necessary dependents; preserve unrelated layout, panels, labels, layers, paths and relationships. Do not replace the original with a similar new template, rasterize it, or use global string replacement. Keep before/after sources and rendered previews. Use `diagram.py patch` for simple ID-targeted SVG attrs/text, `pathway.py diff` for an allowed-ID local XML diff, or source-aware XML/PPTX/drawio code for complex edits. Preserve a requested native format; SVG is not an Office source replacement. Raster-only reconstruction must be disclosed as reconstruction.

For **creation**, map the four roles to a reading order: horizontal sequence, central mechanism plus measured outcome, or a source-required topology. Give the main result the largest useful area; use one restrained categorical palette and ample whitespace. Use short editable labels, clear panel headings, explicit routes and stable semantic IDs. Do not force four equal cards, decorative organisms, repeated icons, a circular graph, or a stock pathway onto unrelated science.

Read [references/composition.md](references/composition.md) to compose reusable native SVG panels and preserve their source-ID mappings. This optional compositor accepts authored geometry and actual SVG assets; it is not a scientific extractor or automatic layout solver. Custom native SVG is equally valid when source layout/semantics require it.

## 3. Preserve scientific meaning in visuals

- **Entities/space:** distinguish gene/protein, family/member, complex/components, material/device/sample and condition-specific states. Retain original names and supported identifiers. A membrane receptor must intersect the membrane; an enclosed object must be in its actual compartment. Show scale bars only with supported physical calibration; otherwise label schematics as not to scale when appropriate.
- **Relations:** explicitly assign source, target, sign, direction, directness, condition and evidence. Activation points to the affected target; inhibition ends in a visible T-bar at that target. Binding/correlation are not automatically directed activation; phosphorylation is not necessarily activation. Uncertain/indirect relations need distinct line style and a matching legend. Spatial adjacency must not accidentally imply causality. Stage-to-stage reading arrows mean workflow sequence, not a biochemical reaction.
- **Data:** read actual CSV/TSV/JSON/XLSX cells, units and error definitions; never type guessed values into marks. Use appropriate axes and a shared scale across comparisons, normally zero-baseline bars. Preserve true zero vs missing, signs, reference groups and supplied uncertainties. No invented n, p-values, replicates or normalized changes. Quantitative color/area/length must share an actual mathematical mapping with its legend; size and fill otherwise carry no hidden numeric meaning. Use labels/line styles in addition to color. For categorical encodings, use color together with a non-color channel (shape, pattern, marker, or explicit text label); color alone is not a safe sole channel. After export, inspect the PNG in grayscale and under a color-vision-deficiency check — if two categories become indistinguishable, change the non-color channel or luminance, not only the hue.
- **Tools:** for supported biological mechanisms read [references/graphs.md](references/graphs.md); for table-driven charts and independent raw-cell roundtrip read [references/charts.md](references/charts.md). Use custom source-aware code for unsupported formats/geometry, rather than altering the workorder to fit helpers. Keep chart axis labels readable after scaling into the full page.

## 4. Real editable artifacts and exports

Use named layers and stable object IDs; keep text as native SVG text/tspan (Matplotlib `svg.fonttype='none'`, PDF fonttype=42). Charts, legends and scientific glyphs remain vectors; a screenshot embedded in SVG is not editable source. Resolve all linked assets. For source native formats use their actual object models. Keep reproducible specs/scripts with artwork.

Select installed fonts supporting actual Chinese/Greek/symbols using `fc-list`/`fc-match` or font discovery; inspect real glyphs. Respect requested physical dimensions, resolution and colors. If unspecified, approximately 180 mm width and 300 DPI with labels at least 7–10 pt at final size are useful defaults, not compulsory constraints. Wrap labels or reallocate space instead of tiny text. Keep one page and avoid tight-bbox cropping that changes physical size.

```sh
python3 /skills/weekly-skill/scripts/diagram.py export --svg /app/output/figure.svg --dpi 300 --out /app/output/export_checks.json
python3 /skills/weekly-skill/scripts/diagram.py audit --svg /app/output/figure.svg --out /app/output/svg_checks.json
```

Always deliver real **SVG + PNG + PDF** for this concrete workorder, plus requested native/additional formats. Export tries Inkscape, rsvg-convert, CairoSVG; inspect inner results/errors. Check signatures, actual PNG pixels/DPI/mode and PDF page count/size/font embedding via Pillow, pdfinfo/pdffonts/PyMuPDF. Pixels should match mm/25.4×DPI within rounding tolerance. A declared font-family does not prove embedding; RGB does not satisfy CMYK. If conversion fails, preserve valid editable source/previews and report partial; never rename an extension or claim unavailable software state.

## 5. Verify and deliver the original contract

Re-read primary passages/captions and source data. Verify each required entity, direction, compartment, number, label, unit, condition, legend and claim against its locator. Compare the relevant paper originals to your actual rendered figure. Check the four-part story, evidence strength, correct figure identity and edit scope. Mechanical checks support this review; they cannot replace scientific interpretation.

Open final PNG and a real PDF page render. Inspect at final physical size and in grayscale for clipping, missing glyphs, cramped labels, obscured arrowheads/T-bars, ambiguous crossings and inconsistent colors. Repair observed issues, then re-export. If viewing is unavailable, record the limit honestly and run geometric/font checks; do not claim visual inspection.

Save change_log.json with input/output hashes and versions, actual element-level before/after, reasons and dependent edits; for new art record creation, not an invented original. Include run.log with actual commands/errors/tool versions, source/encoding maps, element checks, export measurements and remaining uncertainties. Record baseline improvements or elapsed time only when measured; the platform supplies official comparisons and scores.

Fill `/app/output/result.json` with **every original output_contract field, in its original name, nesting and type**, plus original case_id. Map evidence/artifact sidecars into those required fields; do not hide required Chinese fields under an English wrapper. Before finalizing, check the inventory against every requested deliverable and verify referenced files exist, are nonempty and have real format signatures. The JSON finalizer alone does not verify attachment existence. All paths must exist in `/app/output`. Distinguish missing_material, unresolved_science and execution_failure using the case's permitted vocabulary. Validate with `diagram.py finalize --case /input/case.json --report /app/work/report.json --out /app/output/result.json`; read unsupported prose constraints yourself. Final response briefly identifies actual deliverables and material limits.

## Dependencies and boundaries

Python 3.8+ standard library handles SVG composition/graphing, hashing, XML edits and basic checks. Charting uses matplotlib/numpy/Pillow; XLSX uses openpyxl; PDF evidence uses PyMuPDF or pdftotext. Real exports need Inkscape/rsvg-convert or CairoSVG plus system Cairo. JSON Schema validation optionally uses jsonschema. Prefer preinstalled resources; optional install: `python3 -m pip install matplotlib numpy Pillow openpyxl CairoSVG PyMuPDF jsonschema`. No network, API key, external skill or author-specific files are required at evaluation time. Version 2.2.0; interfaces and references are maintained together. Scope is visual scientific communication, not new experimental design/statistics or paper writing.
