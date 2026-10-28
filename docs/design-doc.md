# AI Electrical Takeoff: Design Document

Santiago González · Stage 3 technical assessment · app v1.0.5 (engine 0.6.7)

## 1. Problem

An estimator needs, per electrical sheet, how many fans, lights, switches and receptacles each room has, and what
materials that means. Today this is counted by hand on the drawing. The goal: count automatically, but keep every
number traceable to a mark on the plan, so the estimator can trust it, correct it in seconds, and quote from it.

## 2. Breakdown and build order

| # | Piece | What it does | Why in this order |
|---|-------|--------------|-------------------|
| 1 | PDF ingestion | Reads each page's vectors and text with PyMuPDF; one job per sheet | Everything depends on clean input |
| 2 | Viewport + scale | Finds "ELECTRICAL PLAN - PLAN N", isolates it from the mechanical/finish plans, reads `1/4" = 1'-0"` | Wrong region = wrong counts |
| 3 | Legend | Reads each sheet's legend: symbol geometry becomes templates, text becomes meaning | The legend is the per-sheet "training data" |
| 4 | Symbol detection | Clusters black strokes, matches them to legend templates (rotations), reads nearby codes (D, F, 3D, GFI, 240V) | Geometry gives WHERE, legend gives WHAT |
| 5 | Rooms | Wall mask + flood fill from room labels, open-plan split, Exterior, Attic, B14 closet | Counts are per room |
| 6 | Review UI + CRUD | Plan with marks, per-room table, click a number to see its marks, create/read/update/delete, undo/redo | The estimator is the final authority |
| 7 | Evaluation | Ground truth from human review, metrics per category, golden regression tests | "How do you know it works?" |
| 8 | Bill of materials | Gang boxes, fan-rated boxes, cable runs by type and length, sourced price list, Excel and PDF quote | Turns counts into a quote |

AI choices: the plans are vector, so positions are exact from geometry. A vision LLM is imprecise with coordinates and
miscounts dense symbols, so Claude is used only where language helps: interpreting the legend and flagging ambiguous
symbols for review. It never creates, deletes or places detections: when it was allowed to delete, it removed a
correct 240V receptacle and added an exhaust fan outside the building, so it was reduced to flagging. The system
runs fully without an API key.

## 3. First release

**Does:** analyzes each sheet, detects fans, lights (recessed, wall, exterior), switches (by letter: D, F, 3D, VS, A),
receptacles (AFI, GFI, WP, 240V, MW, DW, FC, half-hot), exhaust fans and detectors; counts per room and per home; full
correction on the plan with undo and redo; BOM with boxes, cable and sourced prices (Home Depot, captured Oct 27, 2026);
Excel and client PDF quote.

**Leaves out:** scanned/raster plans, other drafting standards (tested on 2 public plans: falls back without crashing,
detects little), authentication and multi-tenancy, cloud deployment. Cable tracing ships as beta (off by default).

**Ship criteria:** measured against human-reviewed ground truth on pilot sheets: at least 95% precision and recall on
fans and lights, at least 90% on switches and receptacles, every count backed by a mark, and correcting a sheet takes
minutes and is clearly faster than the estimator's manual count (measured in the pilot).

## 4. Release

- **Pilot:** 2 or 3 estimators on real bids, side by side with their manual takeoff for a few weeks.
- **Versioning:** every result stores the pipeline, model and prompt version. A new version creates a new analysis
  run; runs already corrected are never overwritten, so a model or prompt change cannot break a finished takeoff.
- **Safe changes:** a golden test locks the output of reference plans; any change in counts must be reviewed and
  accepted explicitly. New versions can run in shadow mode (compared, not shown) before switching.
- **Feature flags:** LLM use and cable tracing are switchable per environment.

## 5. Support

- **Accuracy in production:** every correction is logged with before and after. A deleted mark is a false positive, a
  created mark a false negative, a type change a misclassification. That gives accuracy per category and per version
  without extra labeling work.
- **Learning from corrections:** recurring corrections become rules, legend templates or, at scale, training data for a
  detector.
- **New plan styles:** the legend is read per sheet; unknown layouts fall back with a warning and go to a review queue.
- **Bug triage:** every report has the PDF hash and the version, so it can be reproduced exactly; fixed cases are added
  to the golden set.

## 6. Trade-offs and next steps

- Vector-only by design: exact positions, no training data needed. With more time or a team: a trained detector fed by
  corrections, to support scanned plans and new drafting standards.
- Cable runs follow the dashed lines, which show connections, not the real route; length uses a stated routing
  assumption (8 ft ceiling, 48 in switch height, slack, 10% waste). Some millwork is still traced: beta.
- Open-plan room boundaries are a geometric split between labels, drawn on the plan and editable.
- Known limits: two receptacles are missed across the four plans (an AFCI half-hot on Plan 3, the 240V water-heater
  receptacle on Plan 4); cable tracing sometimes follows cabinet lines and misses one fan run on Plan 1; accuracy is
  measured on one house set only.
- Next: multi-sheet projects, integrations with estimating software, cloud deployment with authentication.
