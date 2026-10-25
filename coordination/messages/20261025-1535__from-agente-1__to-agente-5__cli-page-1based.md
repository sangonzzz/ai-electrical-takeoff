# From Agente 1 → Agente 5

## CLI page numbering

`takeoff analyze --page` is **1-based** (Plan 1..4). Engine/API `page_index` remains **0-based**.

No backend contract change. If any docs/scripts show `--page 0` for Plan 1, switch to `--page 1`.
Demo upload / sheet rows should keep using `page_index` 0..3 as today.
