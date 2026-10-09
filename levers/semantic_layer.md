# Lever: semantic_layer

- **Status:** retired — merged into `baseline` 2026-09-29, see below
- **Started:** 2026-09-28
- **`--lever=` flag value:** n/a — no longer a separate lever

## What happened

This was originally planned as **lever 1**, to be compared against a plain-schema
`baseline` (lever 0). Given the cost of a full 1032-question × 7-model run
(~22 hours even after fixing the CPU governor), running the plain-schema version
first — only to immediately supersede it — wasn't worth the time. The user
decided to start the baseline directly from the semantic-layer-annotated schema
instead of running both separately.

**This content now lives in `levers/baseline.md`.** The schema-generation code
(`scripts/build_semantic_schema.py`) and the annotation approach (inline sample
values + auto-detected FK quirks, no invented business prose) are unchanged —
only the bookkeeping changed: it's no longer a distinct `--lever=semantic_layer`
run, it's just what `baseline` sends as the schema.

**Open question this leaves unanswered:** whether the semantic-layer annotations
themselves actually help, vs. plain `schema_text` — there's no same-scale (N=1032)
plain-schema number to compare against anymore. If that comparison ever becomes
worth doing, it would need its own new lever (e.g. `plain_schema_control`) run
from scratch.

See `levers/baseline.md` for the active version of this lever.
