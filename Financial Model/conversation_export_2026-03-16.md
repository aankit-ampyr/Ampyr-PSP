# Financial Model Module 1 — Architecture Discussion
**Date**: 2026-03-16
**Project**: Ampyr-PSP (BESS Sizing Tool)
**Topic**: Ungeared Project IRR — Module 1 Design & Excel Copy Strategy

---

## Context

Three parallel analysis agents completed tracing the Excel financial model (`Off-Grid Solution v8.xlsm`) cell-by-cell. The findings were:

1. **FCFF formula chain** (Equity rows 150-160)
2. **Revenue model** (Solar&BESS Operation → FS)
3. **CAPEX breakdown** (Construction → FS rows 69-89)
4. **OPEX components** (Insurance + BESS sheet → FS row 59)
5. **Tax/Depreciation** (D&T → ungeared tax row 265)
6. **Complete input parameter map** (~25 parameters)

**Conclusion**: ~250 lines of Python (later revised to ~400-500 for monthly precision), no macros, no COM dependency for the pure calculation.

---

## Decision: Module 1 = Ungeared Project IRR

Module 1 targets the **ungeared Project IRR** calculation. This is the first building block of the financial analysis capability.

---

## Excel Copy Strategy

### Requirement
Even for Module 1, the final deliverable for simulated combinations is always the **complete financial Excel workbook** — not just the IRR number. The Excel is the deliverable, not just the calculation engine.

### Copy Lifecycle Policy
**Keep for session duration** — copy persists while user's session is active, deleted on session end/timeout. Allows re-reading outputs without recalculating.

### Design

```
Original Excel (master template)
  │
  │  Never touched at runtime
  │  Lives in: /Financial Model/Off-Grid Solution v8.xlsm
  │
  ├──→ Request arrives
  │     │
  │     ├── 1. Copy to temp file
  │     │     /temp/calc_{session_id}_{timestamp}.xlsm
  │     │
  │     ├── 2. Open copy with xlwings
  │     │
  │     ├── 3. Write inputs → Recalculate
  │     │
  │     ├── 4. Read outputs → Return JSON
  │     │
  │     └── 5. Keep copy until session ends
  │
  └──→ Next request → new copy
```

### ExcelSessionManager Code

```python
# src/excel_manager.py

import shutil
import tempfile
import atexit
from pathlib import Path
from datetime import datetime

class ExcelSessionManager:
    """Manages Excel template copies with session-scoped lifecycle."""

    MASTER_PATH = Path("Financial Model/Off-Grid Solution v8.xlsm")

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.temp_dir = Path(tempfile.mkdtemp(prefix=f"bess_fin_{session_id}_"))
        self.active_copies = {}  # run_id -> Path

    def create_working_copy(self, run_id: str = None) -> Path:
        """Copy master Excel to temp directory for this calculation run."""
        if run_id is None:
            run_id = datetime.now().strftime("%H%M%S")

        copy_name = f"calc_{self.session_id}_{run_id}.xlsm"
        copy_path = self.temp_dir / copy_name
        shutil.copy2(self.MASTER_PATH, copy_path)
        self.active_copies[run_id] = copy_path
        return copy_path

    def get_copy(self, run_id: str) -> Path:
        """Retrieve existing copy for re-reading outputs."""
        return self.active_copies.get(run_id)

    def cleanup(self):
        """Delete all copies and temp directory. Called on session end."""
        for path in self.active_copies.values():
            path.unlink(missing_ok=True)
        self.active_copies.clear()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
```

---

## Module 1 — Complete Architecture

### Hybrid Design

The architecture is **hybrid within Module 1 itself**:

| Phase | Engine | Purpose |
|---|---|---|
| Screening (all configs) | Pure Python | Fast — calculate IRR for 50+ configs in seconds |
| Final output (1-3 selected configs) | COM/xlwings | Produce the populated Excel deliverable |

### Flow

```
                    SCREENING PHASE                    DELIVERABLE PHASE
                    (all configs)                      (1-3 selected)

Step 3 Sizing       Python financial_model.py          ExcelSessionManager
50+ configs ───────→ Monthly FCFF calculation  ────→   Copy master Excel
                     for each config                    Write inputs
                     ~0.1s per config                   Recalculate
                     Returns: Project IRR,              Save populated copy
                     NPV, CAPEX, Payback                User downloads
                              │                                │
                              ▼                                ▼
                     MUST MATCH EXACTLY ◄──── validation ────► SAME IRR
```

### "Must Match Exactly" — Implications

The Python module must replicate the Excel at **monthly granularity**:

```
What you CANNOT simplify:
  ✗ Annual revenue buckets     → Must be monthly (the Excel is monthly)
  ✗ Flat PPA price             → Must apply indexation curves per period
  ✗ Simple degradation         → Must match month-by-month degradation schedule
  ✗ Lump-sum CAPEX             → Must phase across construction months
  ✗ Annual tax                 → Must match D&T monthly ungeared tax calc
  ✗ numpy_financial.irr()      → Must use XIRR with actual dates (monthly cashflows)

What IS straightforward:
  ✓ All formulas are arithmetic (no iteration, no macros)
  ✓ Monthly periods are deterministic (from COD date + project life)
  ✓ Seasonality is a fixed 12-value profile
  ✓ Depreciation is standard (straight-line or reducing balance)
```

This increases the Python module from ~250 lines to ~400-500 lines.

### Development Strategy

```
Phase A: Build Python module with monthly precision
Phase B: Build Excel copy/populate mechanism
Phase C: Validation harness — run both, compare outputs cell-by-cell
Phase D: Build Step 7 Streamlit page
```

**Phase C is critical.** Automated test that:
1. Takes a known config
2. Runs the Python model → gets IRR
3. Copies Excel, populates same config via COM → gets IRR
4. Asserts they match within floating-point tolerance (±0.01%)

This becomes a regression test whenever the Excel model gets updated (v9, v10...).

### File Structure

```
src/
├── financial_model.py          # Pure Python FCFF + Project IRR (monthly)
├── excel_manager.py            # Copy lifecycle + COM write/read
├── financial_config.py         # Input/output cell mappings (YAML or dict)
└── financial_validators.py     # Python vs Excel comparison tests

pages/
└── Step7_Financial.py          # Streamlit UI

Financial Model/
├── Off-Grid Solution v8.xlsm  # MASTER — never modified at runtime
└── templates/                  # Future: additional swappable models

tests/
└── test_financial_model.py     # Validation: Python output == Excel output
```

### Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Screening engine | Pure Python (monthly) | Fast, no Windows dependency for screening |
| Deliverable output | COM-populated Excel copy | User needs the workbook as artifact |
| IRR accuracy | Exact match required | Python replicates Excel monthly logic |
| Copy lifecycle | Session-scoped | Deleted on session end |
| Configs per session | 1-3 Excel workbooks | Sequential processing, no batch/queue needed |
| Validation | Automated Python vs Excel | Regression safety for model updates |

---

## Prior Analysis — Complete Calculation Map

From the three parallel agent analyses:

### Sheets Involved (12 sheets)
1. **Solar&BESS Inputs** — Master input parameters
2. **Solar&BESS Operation** — Hourly/monthly generation simulation
3. **Construction** — CAPEX phasing across construction months
4. **FS (Financial Statements)** — Revenue, OPEX, EBITDA aggregation
5. **D&T (Depreciation & Tax)** — Depreciation schedules, ungeared tax
6. **Equity** — FCFF assembly, XIRR calculation (rows 150-160)
7. **Insurance** — Insurance cost escalation
8. **BESS** — Battery replacement and degradation costs
9. **Assumptions** — Indexation rates, discount rates
10. **Dates** — Period definitions, COD, project life
11. **Seasonality** — 12-month generation profile
12. **Checks** — Validation flags

### Input Parameters (~25)
- Solar capacity (MWp), BESS capacity (MWh/MW)
- PPA price (£/MWh), indexation rate
- CAPEX: EPC, grid connection, development, land
- OPEX: O&M, insurance, land lease, BESS maintenance
- Degradation rate, availability
- Construction timeline, COD date
- Project life (years), discount rate
- Tax rate, depreciation method/rate
- Seasonality profile (12 values)

### Output: Ungeared Project IRR
- **Cell**: Equity sheet, row ~160
- **Method**: XIRR over monthly FCFF cashflows
- **FCFF** = Revenue - OPEX - Ungeared Tax - CAPEX (construction phase)

---

## Next Steps

Proceed with building Module 1:
1. **Phase A**: `financial_model.py` — Pure Python monthly FCFF + XIRR
2. **Phase B**: `excel_manager.py` — Copy lifecycle + COM populate
3. **Phase C**: Validation harness — Python vs Excel comparison
4. **Phase D**: `Step7_Financial.py` — Streamlit wizard page
