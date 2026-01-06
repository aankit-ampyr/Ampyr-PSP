# BESS Sizing Tool - Cloud Application Project Requirements Document (PRD)

**Version:** 1.0
**Date:** January 2026
**Status:** For Developer/Vendor Evaluation

---

## Executive Summary

This document outlines requirements for transforming an existing Streamlit-based Battery Energy Storage System (BESS) Sizing Tool into a full-featured, cloud-hosted web application. The tool optimizes battery storage sizing for solar+storage systems through year-long hourly simulations.

### Project Context
| Aspect | Details |
|--------|---------|
| **Current State** | Working Streamlit prototype with core algorithms |
| **Target Users** | Internal engineering/analysis team (1-10 users) |
| **Scale** | ~100 projects/month initially |
| **Timeline** | 3-4 months |
| **Budget** | To be discussed based on scope |

---

## 1. Business Overview

### 1.1 Problem Statement
Engineering teams need to determine optimal battery capacity for solar+storage projects. This requires:
- Running thousands of hourly simulations across battery sizes
- Enforcing complex operational constraints (binary delivery, cycle limits)
- Analyzing financial viability over 20-year project life
- Comparing multiple system configurations

### 1.2 Solution
A cloud-hosted application that:
- Performs battery sizing optimization with scientific accuracy
- Persists projects and simulation history
- Enables team collaboration on sizing studies
- Provides professional reporting for customer proposals

### 1.3 Success Criteria
- [ ] Team can create, save, and retrieve sizing projects
- [ ] Simulation results match existing Streamlit tool (validated)
- [ ] Multiple users can collaborate on projects
- [ ] System handles 100 projects/month without performance issues
- [ ] 99.5% uptime during business hours

---

## 2. Current System Analysis

### 2.1 Existing Technology Stack
```
Frontend:        Streamlit 1.41.0 (Python-based)
Backend:         Python 3.11+
Data Processing: Pandas 2.2.3, NumPy 2.1.3
Visualization:   Plotly 5.24.1
State:           Streamlit session_state (ephemeral)
Deployment:      Streamlit Cloud (single-page apps)
```

### 2.2 Core Modules to Preserve/Reimplement

| Module | Purpose | Lines | Complexity |
|--------|---------|-------|------------|
| `dispatch_engine.py` | Core simulation (8760 hourly loop) | ~1,200 | High |
| `financial_model.py` | 20-year NPV projection | ~550 | High |
| `degradation_engine.py` | Battery degradation modeling | ~430 | Medium |
| `fuel_model.py` | Willans line DG fuel model | ~300 | Medium |
| `load_builder.py` | Load profile generation | ~470 | Medium |
| `wizard_state.py` | Configuration state machine | ~450 | Medium |
| `config.py` | System constants & defaults | ~100 | Low |

**Total Core Logic:** ~3,500 lines of validated Python

### 2.3 Current UI Flow (5-Step Wizard)

```
Step 1: Setup          → System configuration (load, solar, BESS, DG)
Step 2: Rules          → Dispatch rules (timing, triggers, thresholds)
Step 3: Sizing         → Define capacity ranges for simulation
Step 4: Results        → View/compare/filter configurations
Step 5: Analysis       → Financial projections, sensitivity analysis

Alternative: Quick Analysis → Single configuration deep-dive
```

### 2.4 Dispatch Templates (7 Operating Modes)

| ID | Template Name | DG | Description |
|----|---------------|-----|-------------|
| T0 | Solar + BESS Only | No | Pure solar+battery operation |
| T1 | Green Priority | Yes | DG reactive - runs when battery depleted |
| T2 | DG Night Charge | Yes | DG proactive - pre-emptive night charging |
| T3 | DG Blackout Window | Yes | DG reactive with custom blackout hours |
| T4 | DG Emergency Only | Yes | DG SoC-triggered, anytime operation |
| T5 | DG Day Charge | Yes | DG SoC-triggered, day hours only |
| T6 | DG Night SoC Trigger | Yes | DG SoC-triggered, night hours only |

---

## 3. Functional Requirements

### 3.1 User Management (Priority: HIGH)

| ID | Requirement | Description |
|----|-------------|-------------|
| UM-01 | User authentication | Email/password login with secure session management |
| UM-02 | User roles | Admin (manage users), Analyst (full access), Viewer (read-only) |
| UM-03 | Password reset | Self-service password reset via email |
| UM-04 | Session management | Auto-logout after inactivity, concurrent session handling |

**Recommendation:** For internal team with 1-10 users, simple email/password auth is sufficient initially. Can add SSO later if needed.

### 3.2 Project Management (Priority: HIGH)

| ID | Requirement | Description |
|----|-------------|-------------|
| PM-01 | Create project | New project with name, description, customer reference |
| PM-02 | Save project | Persist all configuration and results to database |
| PM-03 | Load project | Retrieve and restore complete project state |
| PM-04 | List projects | Searchable, sortable project list with filters |
| PM-05 | Project versioning | Save multiple versions/snapshots of a project |
| PM-06 | Clone project | Duplicate existing project as starting point |
| PM-07 | Delete project | Soft delete with recovery option (30 days) |
| PM-08 | Project metadata | Tags, status (Draft/In Progress/Complete), timestamps |

### 3.3 Configuration Wizard (Priority: HIGH)

| ID | Requirement | Description |
|----|-------------|-------------|
| WZ-01 | Step 1: Setup | Configure load profile, solar capacity, BESS params, DG settings |
| WZ-02 | Step 2: Rules | Set dispatch rules, timing windows, SOC thresholds |
| WZ-03 | Step 3: Sizing | Define battery size range, duration classes, DG range |
| WZ-04 | Step 4: Results | View simulation results table with sorting/filtering |
| WZ-05 | Step 5: Analysis | Financial projections, degradation curves, exports |
| WZ-06 | Step navigation | Sequential with validation, ability to go back |
| WZ-07 | Auto-save | Save progress automatically as user advances |
| WZ-08 | Quick Analysis | Alternative single-configuration mode |

### 3.4 Simulation Engine (Priority: CRITICAL)

| ID | Requirement | Description |
|----|-------------|-------------|
| SE-01 | Hourly simulation | 8760-hour year simulation for each configuration |
| SE-02 | Batch processing | Process 100+ configurations per sizing run |
| SE-03 | Template support | All 7 dispatch templates (T0-T6) |
| SE-04 | Binary delivery | Enforce all-or-nothing delivery constraint |
| SE-05 | Cycle tracking | State-transition based cycle counting |
| SE-06 | SOC management | Enforce min/max SOC bounds (5%-95%) |
| SE-07 | Efficiency modeling | Round-trip efficiency 87%, one-way 93.3% |
| SE-08 | DG fuel model | Willans line model with part-load efficiency |
| SE-09 | Degradation model | Calendar aging + cycle-based degradation |
| SE-10 | Progress feedback | Show simulation progress to user |

**Performance Targets:**
- Single configuration: < 500ms
- Batch of 500 configurations: < 30 seconds
- Batch of 1000 configurations: < 1 minutes

### 3.5 Results & Analysis (Priority: HIGH)

| ID | Requirement | Description |
|----|-------------|-------------|
| RA-01 | Results table | Sortable, filterable table of all configurations |
| RA-02 | Configuration comparison | Side-by-side compare up to 3 configurations |
| RA-03 | Detail view | Hourly breakdown for selected configuration |
| RA-04 | Charts | Interactive Plotly charts (delivery %, SOC, power flows) |
| RA-05 | Financial projection | 20-year NPV, IRR, payback analysis |
| RA-06 | Sensitivity analysis | Impact of parameter changes on results |
| RA-07 | Recommendations | Ranked optimal configurations with reasoning |

### 3.6 Data Import/Export (Priority: MEDIUM)

| ID | Requirement | Description |
|----|-------------|-------------|
| DE-01 | Solar profile upload | CSV upload with validation (8760 hours) |
| DE-02 | Load profile upload | CSV upload for custom load patterns |
| DE-03 | Results export CSV | Export simulation results to CSV |
| DE-04 | Results export Excel | Export with multiple sheets (summary, hourly, financial) |
| DE-05 | Configuration export | Export/import project configuration (JSON) |
| DE-06 | Report generation | PDF report with charts, tables, recommendations |

### 3.7 Collaboration Features (Priority: MEDIUM)

| ID | Requirement | Description |
|----|-------------|-------------|
| CO-01 | Project sharing | Share project with team members (view/edit) |
| CO-02 | Comments | Add comments to projects and configurations |
| CO-03 | Activity log | Track who changed what and when |
| CO-04 | Notifications | Email notifications for shared project updates |

---

## 4. Data Model

### 4.1 Core Entities

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     User        │────<│    Project      │────<│  Configuration  │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id              │     │ id              │     │ id              │
│ email           │     │ name            │     │ project_id      │
│ password_hash   │     │ description     │     │ setup_params    │
│ role            │     │ owner_id        │     │ rules_params    │
│ created_at      │     │ status          │     │ sizing_params   │
│ last_login      │     │ created_at      │     │ created_at      │
└─────────────────┘     │ updated_at      │     └─────────────────┘
                        │ tags[]          │              │
                        └─────────────────┘              │
                                │                       │
                                │                       ▼
                        ┌───────▼───────┐     ┌─────────────────┐
                        │ ProjectShare  │     │SimulationResult │
                        ├───────────────┤     ├─────────────────┤
                        │ project_id    │     │ id              │
                        │ user_id       │     │ config_id       │
                        │ permission    │     │ bess_capacity   │
                        │ created_at    │     │ dg_capacity     │
                        └───────────────┘     │ delivery_hours  │
                                              │ delivery_pct    │
                        ┌─────────────────┐   │ total_fuel      │
                        │   Comment       │   │ total_cycles    │
                        ├─────────────────┤   │ npv             │
                        │ id              │   │ hourly_data     │
                        │ project_id      │   │ summary_metrics │
                        │ user_id         │   │ created_at      │
                        │ content         │   └─────────────────┘
                        │ created_at      │
                        └─────────────────┘
```

### 4.2 Configuration Parameters (JSON Schema)

**Setup Parameters (~25 fields):**
```json
{
  "load_mode": "constant|day_only|night_only|seasonal|csv",
  "load_mw": 25.0,
  "solar_capacity_mw": 100.0,
  "solar_source": "default|uploaded",
  "bess_efficiency": 87.0,
  "bess_min_soc": 5.0,
  "bess_max_soc": 95.0,
  "bess_initial_soc": 50.0,
  "bess_daily_cycle_limit": 1.0,
  "dg_enabled": true,
  "dg_operating_mode": "binary|variable",
  "degradation_strategy": "standard|overbuild|augmentation",
  "dg_fuel_curve_enabled": false
}
```

**Rules Parameters (~15 fields):**
```json
{
  "dg_timing": "anytime|day_only|night_only|custom_blackout",
  "dg_trigger": "reactive|soc_based|proactive",
  "dg_charges_bess": false,
  "dg_load_priority": "bess_first|dg_first",
  "soc_on_threshold": 30.0,
  "soc_off_threshold": 80.0,
  "blackout_start": 22,
  "blackout_end": 6,
  "inferred_template": 0
}
```

**Sizing Parameters:**
```json
{
  "mode": "sizing|fixed",
  "capacity_min": 50.0,
  "capacity_max": 200.0,
  "capacity_step": 25.0,
  "durations": [2, 4],
  "dg_min": 0.0,
  "dg_max": 20.0,
  "dg_step": 5.0
}
```

### 4.3 Storage Estimates

| Data Type | Per Project | 100 Projects/Month |
|-----------|-------------|-------------------|
| Configuration JSON | ~5 KB | 500 KB |
| Summary Results | ~50 KB | 5 MB |
| Hourly Data (compressed) | ~2 MB | 200 MB |
| Solar/Load Profiles | ~200 KB | 20 MB |
| **Monthly Total** | ~2.3 MB | **~225 MB** |
| **Annual Total** | - | **~2.7 GB** |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Target |
|--------|--------|
| Page load time | < 2 seconds |
| Single simulation | < 500ms |
| Batch simulation (100 configs) | < 30 seconds |
| API response time | < 200ms (95th percentile) |
| Concurrent users | 10 simultaneous |

### 5.2 Availability & Reliability

| Metric | Target |
|--------|--------|
| Uptime | 99.5% (business hours) |
| Data backup frequency | Daily |
| Backup retention | 30 days |
| Recovery Point Objective (RPO) | 24 hours |
| Recovery Time Objective (RTO) | 4 hours |

### 5.3 Security

| Requirement | Description |
|-------------|-------------|
| Authentication | Secure password hashing (bcrypt/argon2) |
| Session management | JWT or secure cookies, 8-hour expiry |
| Data encryption | TLS 1.3 in transit, AES-256 at rest |
| Input validation | Server-side validation of all inputs |
| SQL injection prevention | Parameterized queries |
| OWASP Top 10 | Address all OWASP Top 10 vulnerabilities |

### 5.4 Scalability

| Aspect | Requirement |
|--------|-------------|
| Users | Handle 10 concurrent, scalable to 50 |
| Projects | 100/month initially, scalable to 1,000 |
| Simulations | 10,000 configurations/day |
| Storage | Start with 10 GB, auto-scale |

---

## 6. Technical Architecture Options

### 6.1 Option A: Modern Full-Stack (Recommended for Best UX)

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│    React/Next.js + TypeScript + Tailwind CSS + Plotly.js    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                            │
│                   REST API (FastAPI)                        │
└─────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Auth Service   │  │ Simulation Svc  │  │  Project Svc    │
│  (FastAPI)      │  │  (Python)       │  │  (FastAPI)      │
└─────────────────┘  └─────────────────┘  └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      PostgreSQL                             │
│              + Redis (caching/sessions)                     │
└─────────────────────────────────────────────────────────────┘
```

**Pros:** Modern, scalable, excellent developer experience, great UI/UX potential
**Cons:** Higher development cost, requires frontend expertise
**Estimated Cost:** $60K - $100K
**Timeline:** 4-5 months

### 6.2 Option B: Python-Centric (Faster MVP)

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend + Backend                       │
│              Streamlit Cloud or Dash Enterprise             │
│                     (Python-based)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                PostgreSQL (Cloud)                           │
│         Supabase / AWS RDS / Azure PostgreSQL               │
└─────────────────────────────────────────────────────────────┘
```

**Pros:** Reuses existing code, faster development, single language
**Cons:** Limited UI flexibility, Streamlit has scalability limits
**Estimated Cost:** $30K - $50K
**Timeline:** 2-3 months

### 6.3 Option C: Hybrid (Best Balance)

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│           Vue.js/Nuxt + Vuetify + Plotly.js                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                        │
│        Existing Python simulation code as modules           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                PostgreSQL + Redis                           │
└─────────────────────────────────────────────────────────────┘
```

**Pros:** Modern UI, reuses Python backend logic, good balance
**Cons:** Still requires frontend development
**Estimated Cost:** $50K - $80K
**Timeline:** 3-4 months

### 6.4 Deployment Recommendation

For internal team of 1-10 users:

| Option | Recommendation |
|--------|---------------|
| **Quick Start** | Streamlit Cloud Teams ($500/month) + Supabase |
| **Better UX** | Vercel (frontend) + Railway/Render (backend) + Supabase |
| **Enterprise** | AWS ECS/Fargate + RDS + CloudFront |

---

## 7. Key Algorithms & Business Logic

### 7.1 Binary Delivery Constraint (CRITICAL)

```python
# Must deliver EXACTLY 25 MW or NOTHING - no partial delivery
if available_power >= TARGET_DELIVERY_MW:
    deliver = True
    delivered_mw = TARGET_DELIVERY_MW  # Always exactly 25 MW
else:
    deliver = False
    delivered_mw = 0  # All-or-nothing
```

### 7.2 Cycle Counting Logic

```
State transitions count as 0.5 cycles each:
- IDLE → CHARGING    = +0.5 cycles
- CHARGING → IDLE    = +0.5 cycles
- IDLE → DISCHARGING = +0.5 cycles
- DISCHARGING → IDLE = +0.5 cycles

Max 2.0 cycles/day enforced as hard constraint
```

### 7.3 Efficiency Model

```
Round-trip efficiency: 87%
One-way efficiency: sqrt(0.87) = 93.3%

Charging:    energy_stored = input × 0.933
Discharging: energy_output = stored × 0.933
```

### 7.4 Financial Model (20-Year NPV)

Key calculations:
- **CAPEX:** BESS ($/MWh + $/MW) + DG ($/MW) + Installation (15%)
- **OPEX:** Fixed O&M + Variable O&M + Fuel (with escalation)
- **Degradation:** 2% calendar + cycle-based (Rainflow counting)
- **Cash Flow:** Revenue - OPEX - Tax (with depreciation shield)
- **NPV:** Sum of discounted cash flows at 8% WACC

---

## 8. Deliverables

### Phase 1: MVP (Month 1-2)
- [ ] User authentication (login/logout)
- [ ] Project CRUD (create, read, update, delete)
- [ ] 5-step configuration wizard
- [ ] Simulation engine (all templates)
- [ ] Basic results table
- [ ] PostgreSQL database setup
- [ ] Cloud deployment

### Phase 2: Core Features (Month 2-3)
- [ ] Solar/load profile upload
- [ ] Configuration comparison
- [ ] Financial projections (20-year)
- [ ] Results export (CSV, Excel)
- [ ] Project sharing (view/edit)
- [ ] Activity logging

### Phase 3: Polish (Month 3-4)
- [ ] Interactive charts
- [ ] PDF report generation
- [ ] Comments on projects
- [ ] Email notifications
- [ ] Performance optimization
- [ ] User documentation

---

## 9. Acceptance Criteria

### 9.1 Simulation Accuracy
- All 7 dispatch templates produce results matching Streamlit tool (±0.1%)
- SOC never exceeds bounds (5%-95%)
- Cycle limits enforced correctly
- Binary delivery constraint never violated

### 9.2 User Experience
- Wizard flow matches current 5-step process
- Page loads < 2 seconds
- Simulation feedback shows progress
- Error messages are clear and actionable

### 9.3 Data Integrity
- Projects saved correctly and retrievable
- No data loss on page refresh
- Concurrent edits handled gracefully
- Backup/restore tested

---

## 10. Vendor Evaluation Questions

When evaluating development companies, ask:

### Technical
1. Experience with Python simulation/scientific computing?
2. Familiarity with energy/battery storage domain?
3. Frontend framework preference and why?
4. How would you handle long-running simulations (>30s)?
5. Database choice and rationale?

### Project Management
6. Development methodology (Agile, Scrum, etc.)?
7. How do you handle scope changes?
8. Communication cadence and tools?
9. Code review and QA process?

### Delivery
10. Can you meet 3-4 month timeline? What's realistic?
11. What does MVP include vs. future phases?
12. Post-launch support and maintenance terms?
13. Source code ownership and licensing?

### Budget
14. Fixed price vs. time & materials?
15. What's included vs. additional cost?
16. Payment milestones?

---

## 11. Appendix

### A. Input Data Format

**Solar Profile CSV (required):**
```csv
timestamp,Solar_Generation_MW
2024-01-01 00:00,0
2024-01-01 01:00,0
2024-01-01 06:00,15.2
2024-01-01 12:00,64.8
...
```
- 8760 rows (full year hourly data)
- Values in MW
- Non-negative values only

### B. Key Output Metrics

| Metric | Description | Unit |
|--------|-------------|------|
| Delivery Hours | Hours meeting 25 MW target | hours |
| Delivery % | Delivery hours / 8760 | % |
| Total Cycles | Cumulative battery cycles | cycles |
| DG Runtime | Hours diesel generator ran | hours |
| Fuel Consumed | Total diesel fuel used | liters |
| Solar Curtailed | Wasted solar energy | MWh |
| NPV | Net Present Value (20 years) | $ |
| IRR | Internal Rate of Return | % |
| Payback | Years to recover investment | years |

### C. Existing Code Repository

The complete working Streamlit application is available for reference:
- All simulation algorithms implemented and tested
- Financial model with 20-year projections
- 7 dispatch templates operational
- Extensive inline documentation

**Source code will be provided to selected vendor under NDA.**

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | Jan 2026 | - | Initial PRD |

---

## Next Steps

1. Review this PRD with internal stakeholders
2. Identify 3-5 development vendors for evaluation
3. Share PRD and request proposals
4. Schedule technical discussions with shortlisted vendors
5. Select vendor and finalize scope/budget
6. Kick off development
