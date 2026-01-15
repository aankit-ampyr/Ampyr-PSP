# BESS Sizing Tool - AmpyrOS Module Integration Plan

---

## 1. Overview

This document details the plan for converting the **BESS Sizing Tool** from a standalone Streamlit application into a pluggable module within the **AmpyrOS** platform.

### 1.1 Current State

| Aspect | Current State |
|--------|---------------|
| **Application Type** | Standalone Streamlit app |
| **Authentication** | None |
| **Data Persistence** | Session state only (ephemeral) |
| **User Management** | Single user |
| **Access Control** | None |

### 1.2 Target State

| Aspect | Target State |
|--------|--------------|
| **Application Type** | AmpyrOS module |
| **Authentication** | SSO via AmpyrOS platform |
| **Data Persistence** | PostgreSQL database |
| **User Management** | Multi-user with roles |
| **Access Control** | Role-based (Admin, Engineer, Viewer) |

---

## 2. Module Manifest

```yaml
# module.yaml
id: bess-sizing
name: BESS Sizing Tool
version: 1.0.0
description: Battery energy storage system optimization and sizing analysis
author: Ampyr Energy Tech
icon: battery-charging
category: design-tools

# Integration configuration
integration:
  type: embedded
  entry_point: /modules/bess-sizing
  api_prefix: /api/v1/bess-sizing
  ui_framework: streamlit

# Module-specific roles
roles:
  - name: admin
    display_name: Administrator
    permissions: [create, read, update, delete, export, manage_users]
  - name: engineer
    display_name: Engineer
    permissions: [create, read, update, export]
  - name: viewer
    display_name: Viewer
    permissions: [read]

# Dependencies on platform services
dependencies:
  - storage
  - notifications
  - audit

# Resource configuration
resources:
  max_projects_per_user: 100
  max_simulations_per_day: 500
  max_file_size_mb: 50
```

---

## 3. Module Structure

### 3.1 Directory Layout

```
modules/bess_sizing/
├── module.yaml                 # Module manifest
├── __init__.py
├── requirements.txt
│
├── sdk/                        # Pure Python business logic (NO UI)
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── dispatch_engine.py      # ← From: src/dispatch_engine.py
│   │   └── templates.py            # Dispatch templates T0-T6
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── financial.py            # ← From: src/financial_model.py
│   │   ├── degradation.py          # ← From: src/degradation_engine.py
│   │   ├── fuel.py                 # ← From: src/fuel_model.py
│   │   └── metrics.py              # ← From: utils/metrics.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── load_builder.py         # ← From: src/load_builder.py
│   │   ├── template_inference.py   # ← From: src/template_inference.py
│   │   └── constants.py            # ← From: src/config.py
│   │
│   └── exceptions.py
│
├── api/                        # FastAPI routes
│   ├── __init__.py
│   ├── app.py
│   ├── dependencies.py
│   │
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── projects.py
│   │   ├── simulations.py
│   │   ├── results.py
│   │   └── exports.py
│   │
│   └── schemas/
│       ├── __init__.py
│       ├── project.py
│       ├── simulation.py
│       └── results.py
│
├── db/                         # Database layer
│   ├── __init__.py
│   ├── models.py
│   └── repositories/
│       ├── __init__.py
│       ├── project_repo.py
│       └── simulation_repo.py
│
├── services/                   # Business services
│   ├── __init__.py
│   ├── project_service.py
│   ├── simulation_service.py
│   └── export_service.py
│
└── ui/                         # Streamlit pages
    ├── __init__.py
    ├── app.py
    └── pages/
        ├── Step1_Setup.py
        ├── Step2_Rules.py
        ├── Step3_Sizing.py
        ├── Step4_Results.py
        └── Step5_MultiYear.py
```

### 3.2 File Migration Map

| Current Location | New Location | Changes Required |
|------------------|--------------|------------------|
| `src/dispatch_engine.py` | `sdk/core/dispatch_engine.py` | Remove st.* imports |
| `src/financial_model.py` | `sdk/analysis/financial.py` | No changes |
| `src/degradation_engine.py` | `sdk/analysis/degradation.py` | No changes |
| `src/fuel_model.py` | `sdk/analysis/fuel.py` | No changes |
| `src/load_builder.py` | `sdk/utils/load_builder.py` | Remove st.* imports |
| `src/template_inference.py` | `sdk/utils/template_inference.py` | No changes |
| `src/config.py` | `sdk/utils/constants.py` | No changes |
| `src/wizard_state.py` | `db/models.py` | Convert to SQLAlchemy models |
| `utils/metrics.py` | `sdk/analysis/metrics.py` | No changes |
| `pages/Step*.py` | `ui/pages/Step*.py` | Add auth checks, use API |

---

## 4. Database Schema

### 4.1 Module Tables

```sql
-- =============================================
-- BESS SIZING MODULE TABLES
-- =============================================

-- Projects
CREATE TABLE bess_projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,              -- References platform users
    name VARCHAR(255) NOT NULL,
    description TEXT,
    customer_reference VARCHAR(100),
    status VARCHAR(20) DEFAULT 'draft',  -- draft, in_progress, completed, archived

    -- Configuration (matches wizard steps)
    setup_config JSONB,                  -- Step 1: System setup
    rules_config JSONB,                  -- Step 2: Dispatch rules
    sizing_config JSONB,                 -- Step 3: Sizing parameters
    financial_config JSONB,              -- Financial analysis settings

    -- Profile references
    load_profile_id UUID,
    solar_profile_id UUID,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE  -- Soft delete
);

-- Simulation runs
CREATE TABLE bess_simulations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID REFERENCES bess_projects(id) ON DELETE CASCADE,
    name VARCHAR(255),
    simulation_type VARCHAR(20),         -- single, optimization, multi_year
    status VARCHAR(20) DEFAULT 'pending', -- pending, running, completed, failed

    -- Configuration snapshot
    config_snapshot JSONB NOT NULL,
    dispatch_template INTEGER,

    -- Timing
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds DECIMAL(10,2),

    -- Results
    summary_metrics JSONB,
    optimization_results JSONB,
    projection_results JSONB,
    hourly_data_path VARCHAR(500),       -- S3 path for large data

    -- Error handling
    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Solar/Load profiles
CREATE TABLE bess_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id UUID NOT NULL,
    profile_type VARCHAR(20) NOT NULL,   -- solar, load
    name VARCHAR(255) NOT NULL,
    source VARCHAR(50),                  -- upload, generated, system

    -- Statistics
    stats JSONB,

    -- Data storage
    data_path VARCHAR(500),              -- S3 path

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_bess_projects_owner ON bess_projects(owner_id);
CREATE INDEX idx_bess_simulations_project ON bess_simulations(project_id);
CREATE INDEX idx_bess_profiles_owner ON bess_profiles(owner_id);
```

### 4.2 Configuration Schema (JSONB)

```json
{
  "setup_config": {
    "load_mode": "constant",
    "load_mw": 25.0,
    "load_day_start": 6,
    "load_day_end": 18,
    "solar_capacity_mw": 67.0,
    "bess_efficiency": 87.0,
    "bess_min_soc": 5.0,
    "bess_max_soc": 95.0,
    "bess_initial_soc": 50.0,
    "bess_daily_cycle_limit": 1.0,
    "dg_enabled": true
  },
  "rules_config": {
    "dg_timing": "anytime",
    "dg_trigger": "reactive",
    "dg_charges_bess": false,
    "dg_load_priority": "bess_first",
    "dg_takeover_mode": true,
    "soc_on_threshold": 20.0,
    "soc_off_threshold": 80.0,
    "inferred_template": 1
  },
  "sizing_config": {
    "capacity_min": 50.0,
    "capacity_max": 200.0,
    "capacity_step": 25.0,
    "durations": [2, 4],
    "dg_min": 0.0,
    "dg_max": 20.0,
    "dg_step": 5.0,
    "optimization_goal": {
      "delivery_mode": "maximize",
      "optimize_for": "min_bess_size"
    }
  }
}
```

---

## 5. API Endpoints

### 5.1 Projects API

```
# Projects CRUD
GET    /api/v1/bess-sizing/projects              # List projects
POST   /api/v1/bess-sizing/projects              # Create project
GET    /api/v1/bess-sizing/projects/{id}         # Get project
PUT    /api/v1/bess-sizing/projects/{id}         # Update project
DELETE /api/v1/bess-sizing/projects/{id}         # Delete project
POST   /api/v1/bess-sizing/projects/{id}/clone   # Clone project

# Configuration endpoints
PUT    /api/v1/bess-sizing/projects/{id}/setup   # Update setup config
PUT    /api/v1/bess-sizing/projects/{id}/rules   # Update rules config
PUT    /api/v1/bess-sizing/projects/{id}/sizing  # Update sizing config
GET    /api/v1/bess-sizing/projects/{id}/validate # Validate config
```

### 5.2 Simulations API

```
# Simulations
POST   /api/v1/bess-sizing/projects/{id}/simulate  # Start simulation
GET    /api/v1/bess-sizing/simulations/{id}/status # Get status
GET    /api/v1/bess-sizing/simulations/{id}/results # Get results
DELETE /api/v1/bess-sizing/simulations/{id}        # Cancel/delete

# Quick analysis
POST   /api/v1/bess-sizing/projects/{id}/quick-analysis  # Single config
```

### 5.3 Results API

```
# Results retrieval
GET    /api/v1/bess-sizing/simulations/{id}/hourly        # Hourly data
GET    /api/v1/bess-sizing/simulations/{id}/recommendations # Recommendations
GET    /api/v1/bess-sizing/simulations/{id}/projection    # Multi-year
POST   /api/v1/bess-sizing/results/compare                # Compare configs
```

### 5.4 Exports API

```
# Exports
GET    /api/v1/bess-sizing/exports/{id}/csv    # Export CSV
GET    /api/v1/bess-sizing/exports/{id}/excel  # Export Excel
GET    /api/v1/bess-sizing/exports/{id}/pdf    # Export PDF report
```

---

## 6. SDK Implementation

### 6.1 Core SDK Interface

```python
# modules/bess_sizing/sdk/__init__.py
"""
BESS Sizing SDK - Pure Python business logic
"""

from .core.dispatch_engine import (
    SimulationParams,
    HourlyResult,
    SummaryMetrics,
    run_simulation,
    calculate_metrics,
)

from .core.templates import (
    DISPATCH_TEMPLATES,
    get_template_info,
)

from .analysis.financial import (
    FinancialConfig,
    FinancialProjection,
    calculate_npv,
    calculate_irr,
)

from .analysis.degradation import (
    DegradationConfig,
    calculate_degradation,
)

from .analysis.metrics import (
    calculate_recommendations,
    find_optimal_size,
)

from .utils.load_builder import (
    build_load_profile,
)

from .utils.template_inference import (
    infer_template,
)

__all__ = [
    # Core
    'SimulationParams',
    'HourlyResult',
    'SummaryMetrics',
    'run_simulation',
    'calculate_metrics',

    # Templates
    'DISPATCH_TEMPLATES',
    'get_template_info',

    # Financial
    'FinancialConfig',
    'FinancialProjection',
    'calculate_npv',
    'calculate_irr',

    # Degradation
    'DegradationConfig',
    'calculate_degradation',

    # Metrics
    'calculate_recommendations',
    'find_optimal_size',

    # Utils
    'build_load_profile',
    'infer_template',
]
```

### 6.2 SDK Usage Example

```python
# Using the SDK directly (for API or CLI)
from bess_sizing.sdk import (
    SimulationParams,
    run_simulation,
    calculate_metrics,
    calculate_recommendations,
)

# Build simulation parameters
params = SimulationParams(
    load_profile=[25.0] * 8760,
    solar_profile=load_solar_profile(),
    bess_capacity=100.0,
    bess_charge_power=25.0,
    bess_discharge_power=25.0,
    bess_efficiency=0.87,
    bess_min_soc=0.05,
    bess_max_soc=0.95,
    dg_enabled=True,
    dg_capacity=10.0,
)

# Run simulation
hourly_results = run_simulation(params, template_id=1)

# Calculate metrics
metrics = calculate_metrics(hourly_results, params)

print(f"Delivery Rate: {metrics.delivery_pct:.1f}%")
print(f"Green Hours: {metrics.green_hours}")
print(f"DG Runtime: {metrics.dg_runtime_hours} hours")
```

---

## 7. Service Layer

### 7.1 Simulation Service

```python
# modules/bess_sizing/services/simulation_service.py

from uuid import UUID
from typing import Optional, Dict, Any
from bess_sizing.sdk import (
    SimulationParams,
    run_simulation,
    calculate_metrics,
    calculate_recommendations,
)
from bess_sizing.db.repositories import ProjectRepository, SimulationRepository
from ampyros.sdk import get_current_user, log_action

class SimulationService:
    def __init__(self, db_session):
        self.db = db_session
        self.project_repo = ProjectRepository(db_session)
        self.simulation_repo = SimulationRepository(db_session)

    async def run_optimization(
        self,
        project_id: UUID,
        config_override: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Run optimization simulation for a project."""

        # Get project
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Merge configuration
        config = self._merge_config(project, config_override)

        # Build profiles
        load_profile = self._build_load_profile(config['setup'])
        solar_profile = await self._get_solar_profile(project)

        # Create simulation record
        simulation = await self.simulation_repo.create(
            project_id=project_id,
            simulation_type='optimization',
            config_snapshot=config,
            status='running'
        )

        try:
            # Run simulations for all configurations
            results = []
            for capacity in self._get_capacity_range(config['sizing']):
                for duration in config['sizing']['durations']:
                    power = capacity / duration

                    params = SimulationParams(
                        load_profile=load_profile,
                        solar_profile=solar_profile,
                        bess_capacity=capacity,
                        bess_charge_power=power,
                        bess_discharge_power=power,
                        bess_efficiency=config['setup']['bess_efficiency'] / 100,
                        bess_min_soc=config['setup']['bess_min_soc'] / 100,
                        bess_max_soc=config['setup']['bess_max_soc'] / 100,
                        dg_enabled=config['setup']['dg_enabled'],
                    )

                    hourly = run_simulation(params, config['rules']['inferred_template'])
                    metrics = calculate_metrics(hourly, params)

                    results.append({
                        'capacity': capacity,
                        'duration': duration,
                        'power': power,
                        'metrics': metrics.to_dict(),
                    })

            # Calculate recommendations
            recommendations = calculate_recommendations(
                results,
                config['sizing']['optimization_goal']
            )

            # Update simulation record
            await self.simulation_repo.update(
                simulation.id,
                status='completed',
                optimization_results=recommendations,
                summary_metrics=recommendations['recommended']['metrics']
            )

            # Log action
            await log_action(
                module='bess-sizing',
                action='simulation.completed',
                resource_id=str(simulation.id),
                details={'config_count': len(results)}
            )

            return recommendations

        except Exception as e:
            await self.simulation_repo.update(
                simulation.id,
                status='failed',
                error_message=str(e)
            )
            raise
```

---

## 8. UI Integration

### 8.1 Authentication Integration

```python
# modules/bess_sizing/ui/app.py

import streamlit as st
from ampyros.sdk import get_current_user, require_permission

def main():
    # Check authentication
    user = get_current_user()
    if not user:
        st.error("Please log in through AmpyrOS")
        st.stop()

    # Store user in session
    st.session_state.user = user

    # Check module access
    if not require_permission('bess-sizing', 'read'):
        st.error("You don't have access to the BESS Sizing module")
        st.stop()

    # Show welcome
    st.sidebar.write(f"Welcome, {user.name}")

    # Load pages based on permissions
    if require_permission('bess-sizing', 'create'):
        # Show full wizard
        pages = [
            "Step1_Setup",
            "Step2_Rules",
            "Step3_Sizing",
            "Step4_Results",
            "Step5_MultiYear",
        ]
    else:
        # Viewer - only results
        pages = ["Step4_Results"]

    # ... rest of app
```

### 8.2 Project Persistence

```python
# modules/bess_sizing/ui/pages/Step1_Setup.py

import streamlit as st
from bess_sizing.api.client import BESSAPIClient

def load_or_create_project():
    """Load existing project or create new one."""

    client = BESSAPIClient()

    # Project selector
    projects = client.list_projects()

    col1, col2 = st.columns([3, 1])

    with col1:
        project_options = ["Create New"] + [p['name'] for p in projects]
        selection = st.selectbox("Project", project_options)

    with col2:
        if st.button("Load"):
            if selection == "Create New":
                name = st.text_input("Project Name")
                if name:
                    project = client.create_project(name=name)
                    st.session_state.project_id = project['id']
            else:
                project = next(p for p in projects if p['name'] == selection)
                st.session_state.project_id = project['id']
                # Load configuration into session state
                load_project_config(project)

def save_step_config():
    """Save current step configuration to database."""

    if 'project_id' not in st.session_state:
        st.warning("Please create or load a project first")
        return

    client = BESSAPIClient()

    # Get current step config from session state
    setup_config = {
        'load_mode': st.session_state.get('load_mode'),
        'load_mw': st.session_state.get('load_mw'),
        'bess_efficiency': st.session_state.get('bess_efficiency'),
        # ... other fields
    }

    # Save to database via API
    client.update_project_setup(
        st.session_state.project_id,
        setup_config
    )

    st.success("Configuration saved!")
```

---

## 9. Migration Steps

### Phase 1: SDK Extraction (Week 5, Days 1-2)

1. **Create module directory structure**
   ```bash
   mkdir -p modules/bess_sizing/{sdk,api,db,services,ui}
   mkdir -p modules/bess_sizing/sdk/{core,analysis,utils}
   mkdir -p modules/bess_sizing/api/{routers,schemas}
   ```

2. **Copy and refactor core modules**
   - Copy `src/dispatch_engine.py` → `sdk/core/dispatch_engine.py`
   - Remove all `import streamlit as st` statements
   - Replace `st.warning()` with `logging.warning()`
   - Replace `st.error()` with `raise ValueError()`

3. **Create SDK public interface**
   - Create `sdk/__init__.py` with all exports
   - Add comprehensive type hints
   - Write unit tests

### Phase 2: Database Layer (Week 5, Days 3-4)

1. **Create SQLAlchemy models**
   - Define Project, Simulation, Profile models
   - Add relationships and indexes

2. **Create repositories**
   - ProjectRepository with CRUD methods
   - SimulationRepository with status tracking

3. **Run migrations**
   ```bash
   alembic revision --autogenerate -m "Add BESS sizing tables"
   alembic upgrade head
   ```

### Phase 3: API Layer (Week 5-6, Days 5-8)

1. **Create FastAPI routers**
   - Projects router with CRUD
   - Simulations router with async support
   - Results router with pagination
   - Exports router

2. **Add Pydantic schemas**
   - Request/response validation
   - JSON schema documentation

3. **Integrate with platform auth**
   - Add auth middleware
   - Check permissions per endpoint

### Phase 4: UI Integration (Week 6, Days 9-10)

1. **Add authentication to Streamlit**
   - Check user from platform
   - Verify module access

2. **Add project persistence**
   - Load/save project via API
   - Project selector UI

3. **Testing**
   - End-to-end testing
   - Permission testing

---

## 10. Business Logic Preservation

### 10.1 Critical Rules to Maintain

| Rule | Description | Implementation |
|------|-------------|----------------|
| **Binary Delivery** | Always 25 MW or 0, never partial | Check in dispatch_engine.py |
| **Cycle Limits** | Max 2.0 cycles per day | Enforced in state machine |
| **SOC Bounds** | 5% - 95% operational window | Clamping in charge/discharge |
| **Efficiency** | 87% round-trip = 93.3% one-way | Applied in energy calculations |
| **Solar-Only Charging** | No grid charging | No external energy source |

### 10.2 Dispatch Templates

All 7 templates (T0-T6) must work identically:

| Template | Description | Key Behavior |
|----------|-------------|--------------|
| T0 | Solar + BESS Only | No DG at all |
| T1 | Green Priority | DG as last resort |
| T2 | DG Night Charge | Proactive night charging |
| T3 | DG Blackout Window | Custom hours when DG blocked |
| T4 | DG Emergency Only | SOC-triggered, anytime |
| T5 | DG Day Charge | SOC-triggered, day only |
| T6 | DG Night SoC Trigger | SOC-triggered, night only |

---

## 11. Verification Checklist

### SDK Verification
- [ ] All 7 dispatch templates produce identical results to current app
- [ ] Binary delivery constraint enforced
- [ ] Cycle limits enforced correctly
- [ ] SOC bounds never violated
- [ ] Efficiency calculations match

### API Verification
- [ ] Project CRUD works correctly
- [ ] Simulations run and complete
- [ ] Results return correct data
- [ ] Exports generate valid files
- [ ] Error handling is robust

### UI Verification
- [ ] Authentication flow works
- [ ] Projects save and load correctly
- [ ] All wizard steps function
- [ ] Results display correctly
- [ ] Exports download properly

### Integration Verification
- [ ] Platform auth passes to module
- [ ] Permissions enforced correctly
- [ ] Audit logs captured
- [ ] File storage works
