# Helper interfaces (v2.0.3)

All examples below are **synthetic interface demonstrations**, never formal case results. Replace paths/fields/constraints with the current case. Run `--help` for CLI options. All paths to table sources in a plot specification are relative to that specification, or absolute runtime paths.

## v2.0.3 grouped-category extension

Grouped bars now align by the first series' categorical `x` registry instead of requiring identical physical table order. Each later series must contain exactly the same unique keys. Source order `B,A` against registry `A,B` is reordered with complete row bundles, and its logical row permutation is recorded in `source_map.json.category_alignments`. No missing-value creation or aggregation is allowed. Run `check_category_alignment.py --map source_map.json` after a real reordering and independently run `verify_sources.py`.

## Table inspection and plotting

```
python3 /skills/weekly-skill/scripts/charts.py inspect --source /input/data.csv --out /app/work/table.json
python3 /skills/weekly-skill/scripts/charts.py render --spec /app/output/plot_spec.json --out /app/output
```

Minimal synthetic input CSV:
```
group,value,sd
Demo-A,4,0.3
Demo-B,7,0.8
```

Synthetic configuration (not a formal answer):
```json
{
  "name":"figure",
  "sources":{"s":{"path":"/input/data.csv"}},
  "style":{"width_mm":180,"height_mm":90,"dpi":300,"font_size":9,"columns":1,"palette":["#0072B2"]},
  "panels":[{"kind":"bar","title":"Synthetic demo","xlabel":"Demo group","ylabel":"Demo measurement (a.u.)",
    "series":[{"source":"s","x":"group","y":"value","label":"Demo values","error":"sd","error_kind":"SD supplied by synthetic example"}]}]
}
```

Illustrative generated files: `figure.svg`, `figure.png`, `figure.pdf`, `plot_spec.json`, `source_map.json`, `export_checks.json`. Illustration of a map entry: `element_id=data-000001`, value=4, source column=value, logical row=2. This is an interface illustration, not a prepared official output. The renderer actually reads the CSV at execution.

Configuration:
- `sources`: ID → `{path, sheet?}`; `sheet` is Excel sheet name or zero-based index, default 0. CSV delimiter comma; TSV tab; UTF-8 BOM allowed; JSON list of row objects. Irregular tables must be normalized into a runtime derivative with its own provenance (never lose original cells).
- `panels`: list, `kind` in `bar,line,scatter,box,heatmap,pie`; each with `series` list. Titles, xlabel/ylabel must include actual units as appropriate. Supported axes: `xscale,yscale,xlim,ylim`; `legend,legend_loc,label_rotation`. Physical layout through `style.columns,width_mm,height_mm,font_size,font_family` (list or string), `font_path` (installed font), `line_width,palette,dpi,transparent`.
- `series`: `source,x,y,label,color?`; selection by `where` exact textual equality and/or `rows` logical row numbers (first data row 2). No automatic aggregation. `sort_by` explicit numeric column only. `categorical_x=true` for categorical line/scatter. Stable category order must match across grouped bar series. For categorical x order missing levels, explicitly reindex without inventing values or use custom script.
- `label_column` and `color_column`, both or neither: the selected rows must contain one non-blank label and one non-blank swatch. Those values replace `label` and `color` on the marks and in the legend. Synthetic check, not a formal case: `python3 /skills/weekly-skill/scripts/check_legend_series.py --spec plot_spec.json --svg figure.svg`. Exit 0 only when every legend text and swatch equals that table pair, in series order.
- `error` symmetric distance column, or both `error_low,error_high` distance columns; `error_kind` mandatory. Error bounds-to-distances conversion is a documented preprocessing step. `point_size` for scatter, `marker` for line. Helper supports y errors; add x errors/stacking/horizontal bars in a source-aware custom script if required.
- `box`: raw observation y; x identifies group. Default whiskers 1.5 IQR, explicitly set panel `whis` if specified; summary-only tables require `Axes.bxp` custom plot with declared stats. No invented replicates. Multi-series boxes use offsets; complex groups need custom positioning and legend.
- `heatmap`: exactly one series with `x` category, `y` category and `value` numeric column in a long-form rectangular grid. Unique complete coordinates required. Panel `cmap,vmin,vmax,colorbar_label`. No automatic pivot aggregation or missing-cell fill. Vector pcolormesh; map group plus cell indices.
- `pie`: one nonnegative positive-total series, x category/y value. Actual sector angles checked. Prefer only when requested; `startangle` optional.
- `annotations`: panel list of `{x,y,text,source,ha?,va?,fontsize?}` in data coordinates. Source must identify supplied n/p-value/text, not infer it. Add bracket geometry in a custom source-aware script if needed.

Renderer rejects missing columns, bad/missing numeric cells, duplicate coordinates/categories, mismatched grouped orders, negative errors, unsupported semantics. Nonzero exit code means actual failure. Old artifacts may remain: inspect modification times and checks; never report stale files as new. Fix upstream issue and rerun, or retain honest partial artifacts. Font/bounds/clipping findings produce `needs_review`; actual geometry and files still saved for repair.

Source map point IDs for line/scatter are `SVG-group:point-index`, heatmap `SVG-group:cell-row-col`; they refer to individual data positions within an editable SVG group. Some SVG renderers use marker `<use>` elements. Do not claim each point has a standalone `<path>` ID. Box entries include every raw observation and n. PDF/export flags do not verify semantics or all collisions.

## Shared SVG and result helpers

```
python3 /skills/weekly-skill/scripts/diagram.py audit --svg /app/output/figure.svg --out /app/output/svg_checks.json
python3 /skills/weekly-skill/scripts/diagram.py patch --svg /input/original.svg --changes /app/work/edits.json --out /app/output/revised.svg
python3 /skills/weekly-skill/scripts/diagram.py export --svg /app/output/revised.svg --dpi 300 --out /app/output/export_checks.json
python3 /skills/weekly-skill/scripts/diagram.py finalize --case /input/case.json --report /app/work/final_report.json --out /app/output/result.json
```

`patch` edit list: `[{"op":"attrs","id":"actual-source-id","value":{"fill":"#0072B2"}}]` or `{"op":"text","id":"actual-text-id","value":"source-supported label"}`. IDs must already exist; no ID renaming/events. Retains XML subtree semantics (serialization/namespace formatting can change), refuses same input/output path. Complex tspan text requires specific IDs or source-aware XML/native editor. Generated `.changes.json` is actual before/after and SHA256 record; add scientific rationale from materials. Do not edit data geometry without also updating the scientific map and axes consistently.

`export` tries actual installed converters (Inkscape → rsvg-convert → CairoSVG), captures real errors; no fake extension conversion. Inspect its inner status, not just top-level command completion. SVG physical width/height control PNG size. PNG DPI metadata written by Pillow; independently verify physical pixel dimensions. RGB by default; CMYK/profile requirements need actual color conversion and separate verification. `audit` checks native text/IDs/XML only, not science or label overlaps.

`finalize` supports JSON schema properties/required, list of names or `{name/field/key,type}`, `fields` wrapper, or plain field-name maps. Required values must be filled from actual execution; case_id is retained from original. JSON schema validation uses jsonschema if present; helper's fallback types are limited. Read and validate unsupported constraints yourself. It rejects mismatched case_id/fields before atomically replacing result. Never use a helper's unsupported-contract silence as successful validation.

## Independent source roundtrip

```
python3 /skills/weekly-skill/scripts/verify_sources.py --map /app/output/source_map.json --out /app/output/source_checks.json
```

Reloads each raw source cell and its file SHA256, compares against the map, checks recorded direct geometry, and builds a reverse index by file/sheet/row/column. Nonzero exit on changed source/bad mapping. Requires map schema emitted by `charts.py`; custom transformations need explicit formula/lineage checks rather than blindly reusing this direct-value verifier. A source-check pass does not replace scientific review or before/after image inspection.


## Required-artifact reopening (v1.1.0)

Before finalization write a manifest from the actual workorder, e.g. the following **synthetic interface example only**:

```json
{"artifacts":[{"path":"figure.svg","format":"svg","width_mm":180,"height_mm":90},{"path":"figure.png","format":"png","width_mm":180,"height_mm":90,"dpi":300},{"path":"figure.pdf","format":"pdf","width_mm":180,"height_mm":90}]}
```

Run `python3 /skills/weekly-skill/scripts/validate_delivery.py --root /app/output --manifest /app/work/delivery_manifest.json --out /app/output/delivery_checks.json`.

Paths are relative to the output root, formats explicit. Exit codes: 0 verified checks passed, 1 failed/missing required artifact, 2 needs review because a check lacks tools or native format inspection. JSON contract checks alone cannot detect nonexistent export paths; this checker actually reopens files. PDF uses PyMuPDF if available, then actual pdftoppm rendering; the fallback may still need pdfinfo dimensions. Office ZIP validity cannot establish native object editability. Scientific interpretation and full visual review remain required.

Version 1.1.0 also rejects nonpositive logarithmic coordinates/error bounds rather than merely exporting hidden marks. If the real workorder requires censored/nonpositive data, use an explicitly documented source-aware representation instead of silently dropping it.
