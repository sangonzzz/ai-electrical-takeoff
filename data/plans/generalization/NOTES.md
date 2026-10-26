# Generalization test notes (Agente 7)

## Sources (public city / county plan PDFs)

City ADU portals (Oakland, Elk Grove, Alameda County) returned **403/Cloudflare**
from this environment, so those exact Escondido-style ADU sets could not be
downloaded here. Used instead:

| File | Source | Why |
|------|--------|-----|
| `data/plans/generalization/longview_residential_template.pdf` | [Longview TX DocumentCenter](https://www.longviewtexas.gov/DocumentCenter/View/13811/Residential-Plan-Template) | Residential plan template with an **ELECTRICAL PLAN EXAMPLE** sheet (page index 4) and a symbol legend (receptacle, GFI, switch, fan, smoke…). |
| `data/plans/generalization/pbg_electrical.pdf` | [Palm Beach Gardens FL DocumentCenter](https://www.pbgfl.gov/DocumentCenter/View/20351) | Electrical drawing set: symbol legend page + floor power plans (more commercial language). |

Probe: `uv run python eval/scripts/generalization_probe.py` (`use_llm=False`, no engine tuning).

## Results (honest)

All three probed pages **failed before detection**:

```
ValueError: page N: no bold 'ELECTRICAL PLAN - PLAN N' title found
```

### What this means

| Area | Observation |
|------|-------------|
| **Viewport / title** | Engine requires a bold title matching Escondido’s `ELECTRICAL PLAN - PLAN N`. Longview uses “ELECTRICAL PLAN EXAMPLE”; PBG has “ELECTRICAL SYMBOL LEGEND” / room numbers — **no Escondido-style title**. Viewport discovery never starts. |
| **Legend** | Not reached. Longview’s legend uses different names (GFI vs GFCI wording, “RECESSED LIGHT FIXTURE”, etc.). Even with a viewport, template matching would need legend text flexibility. |
| **Overlay** | No `SheetResult` → no overlay PNG produced. |
| **Rooms / symbols** | Not reached. |

### What works on Escondido (contrast)

Same CLI + docker demo succeed on `data/plans/escondido_plans.pdf` (title cell + legend present).

### Recommendation (not implemented)

Do **not** hardcode city names. Soften title matching (regex / “ELECTRICAL PLAN” without requiring `- PLAN N`) as a follow-up owned by Agente 2 — only after product agreement. This probe stays failing on purpose until then.
