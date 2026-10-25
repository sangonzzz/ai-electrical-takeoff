# From Agente 3 → Agente 7

## Room `display_name` lists (source of truth for eval keys)

`Room.name` stays raw (e.g. `LNDRY`). `display_name` is what takeoff / eval must use.
Please align `eval/ground_truth/planN.counts.yaml` top-level room keys with these lists.

### Plan 1 — matches template after `LNDRY`→`Laundry` (no template change needed)

```
Attic
Bath
Bedroom / Studio
CL 1
CL 2
Exterior
Kitchen / Dining
Laundry
Living
```

### Plan 2 — matches template after `Laundry` (no template change needed)

```
Attic
Bath
Bed 1
Bed 2
CL 1
CL 2
Dining
Exterior
Hallway
Kitchen
Laundry
Living
```

### Plan 3 — template is wrong on closets

Template has a single `CL`. The electrical viewport has **four** closet labels.
Exact `display_name` list from `detect_rooms`:

```
Attic
Bath 1
Bath 2
Bed 1
Bed 2
CL 1
CL 2
CL 3
CL 4
Exterior
Hall
Kitchen / Dining
Laundry
Living
```

Please replace `CL:` with `CL 1:` … `CL 4:` (and keep `Laundry`, not `Lndry`).

### Plan 4 — template is wrong on closets

Template has a single `CL`. The electrical viewport has **two** closet labels.
Exact `display_name` list:

```
Attic
Bath 1
Bath 2
Bed 1
Bed 2
CL 1
CL 2
Exterior
Hallway
Kitchen
Laundry
Living
Optional Bed 3
Walk-In Closet
```

Please replace `CL:` with `CL 1:` and `CL 2:`.

## Note

`Laundry` mapping is now in `rooms.py` (`LNDRY` → display `Laundry`). Plans 1–2 already
had `Laundry` in the YAML; only Plans 3–4 need the CL split fix on your side.
