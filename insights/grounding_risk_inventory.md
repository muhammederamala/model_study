# Grounding risk inventory before the run finishes

This is a snapshot taken while 104 of 1,032 grounded Qwen 14B questions were still unattempted: 60 in `wta_1` and 44 in `world_1`. [The CSV](grounding_risk_inventory.csv) lists every pending ID, its question, prompt-based risk tags, the evidence, and a review action. Regenerate a fresh inventory with `python3 scripts/audit_grounding_risks.py` while the run is active. The scanner uses question text and grounding context only; it does not inspect gold SQL or future model SQL. **A flag is a risk to inspect, not a prediction that the query will fail.** Lower-priority questions can still fail.

## High-priority cases

- `wta_1` (33): 9, 29, 50, 88, 158, 225, 226, 281, 316, 410, 415, 419, 441, 458, 459, 505, 517, 541, 567, 625, 669, 672, 677, 678, 744, 756, 817, 853, 877, 907, 927, 959, 981. Main risks: winner/loser join role, event rank points versus dated rankings, two-tournament or two-year logic, and duplicate players across matches.
- `world_1` (29): 671, 679, 687, 690, 719, 728, 750, 757, 767, 776, 779, 785, 790, 823, 832, 834, 835, 843, 852, 859, 863, 870, 925, 930, 938, 952, 970, 1017, 1024. Main risks: city versus country population, `any` comparisons, language negation/intersection, official language versus percentage, and one-to-many joins.

## Other pending cases

- `wta_1` medium (17): 40, 60, 126, 184, 204, 268, 299, 365, 396, 480, 638, 731, 783, 849, 886, 895, 928. Lower (10): 17, 129, 162, 209, 329, 446, 483, 603, 609, 980.
- `world_1` medium (13): 751, 761, 803, 829, 888, 890, 920, 937, 985, 991, 993, 1022, 1031. Lower (2): 778, 904.

## Review after all 1,032 results arrive

Join the saved SQL and execution results to this frozen inventory. For each risk family, inspect both failures **and successes**, then revise the grounding rule across the database rather than patching individual dev questions. Existing observed regressions also need review: IDs 37, 130, 133, 292, 450, 478, 516, 530, 691, 697, 742, 978, and 988. The current candidate matcher can promote a correct but irrelevant column (for example `TV_series.Air_Date` for a cartoon question), display both sides of an ambiguous role, and suggest extra joins. Keep the active runner, catalogs, and saved results unchanged until this run is complete. Validate any revised rules on separate paired questions so a recovered failure does not hide a new regression.
