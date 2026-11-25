# Changelog

## v2.3.0 — 2026-11-25

Based on the supplied v1.0.1 source, with one focused addition: independent chart source-data reconciliation.

- Added `scripts/chart_audit.py` for Python 3.8+, using the standard library for CSV, TSV, and JSON-array sources; optional XLSX support uses preinstalled openpyxl and reports its absence explicitly.
- Added source-cell hashing/reloading, decimal-safe raw/value/mark comparisons, explicit zero-versus-missing checks, declared-unit consistency, legend count/order/label/color/marker checks, series-keyed style checks, detailed reports, and a reverse cell index.
- Documented the reusable map interface and synthetic example. Added mandatory redraw/map-update/rerun guidance for source-data changes while keeping scientific review separate from mechanical success.
- Tested valid CSV, TSV/elements, JSON, and preinstalled-openpyxl XLSX maps, data edited without redraw, wrong legend label/color, zero-versus-missing mismatches, empty-map failure, and standard-library-only XLSX failure using synthetic files in `/tmp`.
