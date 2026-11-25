# Changelog

## 2.4.0 — 2026-11-25

- Added the standard-library `scripts/edit_audit.py` pre-export check for native SVG revisions: exact declared-versus-actual per-ID differences, original ID/duplicate/hash safeguards, per-ID digests, revised-image reference checks, and explicit source-preservation limitations; integrated its use and synthetic example into the workflow documentation. This is mechanical verification only, not semantic certification.
