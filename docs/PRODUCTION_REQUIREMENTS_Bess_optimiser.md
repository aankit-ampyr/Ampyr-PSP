# BESS Sizing Tool - Production Application Requirements

**Document Version:** 1.0
**Date:** January 2026
**Status:** Ready for Contractor Estimation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Project Overview](#2-project-overview)
3. [Technical Architecture](#3-technical-architecture)
4. [Functional Requirements](#4-functional-requirements)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Delivery Phases](#6-delivery-phases)
7. [Deliverables & Acceptance Criteria](#7-deliverables--acceptance-criteria)
8. [Reference Materials](#8-reference-materials)

---

## 1. Executive Summary

### 1.1 Project Goal

Transform an existing Python Streamlit prototype into a production-grade web application for Battery Energy Storage System (BESS) sizing and optimization. The application will feature professional UI, multi-user authentication, AI-powered analysis, and robust deployment infrastructure.

### 1.2 Current State

- **Existing Prototype:** Functional Streamlit application with complete simulation engine
- **Core Logic:** Python-based dispatch simulation, optimization algorithms, visualization
- **Code Available:** Full source code provided as reference/starting point for backend logic

### 1.3 Target State

- **Production Web Application:** React frontend + FastAPI backend
- **Multi-User System:** Role-based access with JWT authentication
- **AI Integration:** Hybrid local/cloud AI for analysis and recommendations
- **Deployment:** Docker-based, initially hosted on local desktop with internet access via Cloudflare Tunnel

---

## 2. Project Overview

### 2.1 Business Context

The BESS Sizing Tool helps energy professionals determine optimal battery storage configurations for solar+storage systems. It simulates year-long battery operations considering:

- Binary delivery constraints (full target delivery or nothing)
- Battery cycle limits and degradation
- State of Charge (SOC) management
- Diesel Generator (DG) backup integration
- Green energy percentage targets

### 2.2 Target Users

| Role | Description | Primary Functions |
|------|-------------|-------------------|
| **Admin** | System administrators | User management, system settings, full access, audit logs |
| **Analyst** | Technical users | Run simulations, configure scenarios, use AI features, export data |
| **Viewer** | Read-only users | View shared results/reports, no simulation access |
| **Management** | Executive users | View dashboards, reports, AI-generated insights, no technical configuration |

### 2.3 Key Features Overview

| Feature Category | Description |
|------------------|-------------|
| **Simulation Engine** | Year-long (8760 hour) battery dispatch simulation |
| **Optimization** | Multi-dimensional sweep (Solar × BESS × Container × DG) |
| **Visualization** | Interactive charts, heatmaps, time-series plots |
| **AI Assistant** | Natural language queries, recommendations, report generation |
| **Data Management** | Save/load simulations, export to CSV/Excel |
| **Multi-Project** | Organize simulations by project/client |

---

## 3. Technical Architecture

### 3.1 Technology Stack

| Layer | Technology | Justification |
|-------|------------|---------------|
| **Frontend** | React 18+ | Professional UI, component ecosystem, large talent pool |
| **UI Components** | MUI (Material-UI) or Ant Design | Enterprise-grade component library |
| **Charts** | Plotly.js or Recharts | Interactive visualizations |
| **Backend** | FastAPI (Python 3.10+) | Async performance, auto-generated API docs, reuse existing simulation code |
| **Database** | PostgreSQL 15+ | Relational data, JSON support, industry standard |
| **Cache** | In-memory (Phase 1), Redis optional | Session-based simulation cache |
| **Authentication** | Custom JWT | Self-contained, no external dependencies |
| **Containerization** | Docker + Docker Compose | Consistent deployment, easy scaling |
| **Reverse Proxy** | Nginx | Serve React build, route API calls |
| **Tunnel** | Cloudflare Tunnel | Secure internet access without static IP |

### 3.2 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              INTERNET                                   │
│                                  │                                      │
│                    bess.yourdomain.com (HTTPS)                          │
└──────────────────────────────────┼──────────────────────────────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │  Cloudflare Tunnel  │
                        └──────────┬──────────┘
                                   │
┌──────────────────────────────────┼──────────────────────────────────────┐
│                        HOST MACHINE (Desktop)                           │
│  ┌───────────────────────────────┼───────────────────────────────────┐  │
│  │                      DOCKER COMPOSE                               │  │
│  │                               │                                   │  │
│  │                               ▼                                   │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │                      NGINX (:80/:443)                       │  │  │
│  │  │            Static Files + Reverse Proxy                     │  │  │
│  │  └───────────────┬─────────────────────────────┬───────────────┘  │  │
│  │                  │                             │                  │  │
│  │          /api/*  │                    /*       │                  │  │
│  │                  ▼                             ▼                  │  │
│  │  ┌───────────────────────┐       ┌───────────────────────────┐   │  │
│  │  │      FASTAPI          │       │        REACT              │   │  │
│  │  │      (:8000)          │       │    (Static Build)         │   │  │
│  │  │                       │       │                           │   │  │
│  │  │  • Auth endpoints     │       │  • Login/Dashboard        │   │  │
│  │  │  • Simulation API     │       │  • Simulation Wizard      │   │  │
│  │  │  • Project CRUD       │       │  • Results Visualization  │   │  │
│  │  │  • AI endpoints       │       │  • Admin Panel            │   │  │
│  │  │  • Export endpoints   │       │  • AI Chat Interface      │   │  │
│  │  └───────────┬───────────┘       └───────────────────────────┘   │  │
│  │              │                                                    │  │
│  │              ▼                                                    │  │
│  │  ┌───────────────────────┐       ┌───────────────────────────┐   │  │
│  │  │     POSTGRESQL        │       │    FILE STORAGE           │   │  │
│  │  │      (:5432)          │       │    (Docker Volume)        │   │  │
│  │  │                       │       │                           │   │  │
│  │  │  • Users & Auth       │       │  • Saved Simulations      │   │  │
│  │  │  • Projects           │       │    (Parquet + JSON)       │   │  │
│  │  │  • Simulation Index   │       │  • Solar Profiles (CSV)   │   │  │
│  │  │  • AI Conversations   │       │  • Export Files           │   │  │
│  │  │  • Audit Logs         │       │                           │   │  │
│  │  └───────────────────────┘       └───────────────────────────┘   │  │
│  │                                                                   │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

### 3.3 Data Architecture

#### 3.3.1 PostgreSQL Schema (Core Tables)

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User accounts | id, email, password_hash, role, created_at, is_active |
| `projects` | Project organization | id, name, owner_id, created_at, settings_json |
| `simulations` | Simulation index | id, project_id, user_id, name, created_at, file_path, summary_json |
| `ai_conversations` | AI chat history | id, user_id, project_id, simulation_id, messages_json, created_at |
| `audit_logs` | User activity tracking | id, user_id, action, resource, details_json, timestamp |

#### 3.3.2 File Storage Structure

```
/data/
  ├── saved_simulations/
  │     └── {project_id}/
  │           └── sim_YYYYMMDD_HHMMSS/
  │                 ├── metadata.json      # Config, rules, ranges, summary
  │                 └── results.parquet    # All result rows (compressed)
  │
  ├── solar_profiles/
  │     └── {project_id}/
  │           └── *.csv                    # Uploaded solar profiles
  │
  └── exports/
        └── {user_id}/
              └── *.csv, *.xlsx            # Temporary export files
```

#### 3.3.3 Simulation File Format

**metadata.json:**

```json
{
  "id": "sim_20240115_143022",
  "display_name": "Summer Peak Analysis",
  "created_at": "2024-01-15T14:30:22Z",
  "created_by": "user@email.com",
  "project_id": "project_123",

  "setup": {
    "load_mw": 25,
    "bess_efficiency": 87,
    "bess_min_soc": 5,
    "bess_max_soc": 95,
    "dg_enabled": true,
    "dg_capacity": 30
  },

  "dispatch_rules": {
    "inferred_template": "T1",
    "dg_charges_bess": false,
    "night_start": 18,
    "night_end": 6
  },

  "optimization_ranges": {
    "solar_min_mw": 50,
    "solar_max_mw": 200,
    "solar_step_mw": 25,
    "bess_min_mwh": 0,
    "bess_max_mwh": 150,
    "bess_step_mwh": 5
  },

  "targets": {
    "green_energy_target_pct": 50,
    "max_wastage_pct": 20
  },

  "summary": {
    "total_configs_tested": 2000,
    "viable_count": 342,
    "min_solar_for_target": 75,
    "min_bess_for_target": 50
  }
}
```

**results.parquet:** Contains all simulation result rows with columns:

- Configuration: solar_capacity_mw, bess_capacity_mwh, duration_hr, power_mw, containers, dg_capacity_mw
- Metrics: delivery_pct, green_energy_pct, green_hours_pct, wastage_pct
- Hour counts: delivery_hours, load_hours, green_hours, dg_runtime_hours, dg_starts
- Other: total_cycles, unserved_mwh, fuel_liters, is_viable

### 3.4 Caching Strategy

| Cache Type | Technology | Purpose | Expiration |
|------------|------------|---------|------------|
| **Session Cache** | In-memory (app) | Store active simulation results for fast analysis | Session-based (logout clears) |
| **API Cache** | FastAPI built-in | Cache expensive computations | Time-based (configurable) |

**Session Cache Behavior:**

- User runs simulation (e.g., 2000 configs) → Results stored in memory
- User analyzes, filters, visualizes → Fast access from cache
- User saves simulation → Persisted to Parquet + JSON
- User logs out or session expires → Cache cleared
- User loads saved simulation → File loaded into cache for fast access

---

## 4. Functional Requirements

### 4.1 Authentication & Authorization

#### 4.1.1 Authentication

| Feature | Description |
|---------|-------------|
| **Login** | Email + password authentication |
| **JWT Tokens** | Access token (short-lived) + Refresh token (long-lived) |
| **Password Reset** | Email-based password reset flow |
| **Session Management** | Track active sessions, force logout capability |
| **Password Requirements** | Minimum 8 characters, complexity rules configurable |

#### 4.1.2 Role-Based Access Control

| Role | Projects | Simulations | AI Features | Admin Panel | Export |
|------|----------|-------------|-------------|-------------|--------|
| **Admin** | Full CRUD | Full CRUD | Full access | Full access | Yes |
| **Analyst** | View assigned, create own | Full CRUD on accessible | Full access | No | Yes |
| **Viewer** | View assigned | View only | View insights only | No | Limited |
| **Management** | View all | View summaries | View insights, reports | No | Reports only |

### 4.2 Project Management

| Feature | Description |
|---------|-------------|
| **Create Project** | Name, description, assign users |
| **Project Settings** | Default simulation parameters per project |
| **User Assignment** | Assign users to projects with specific roles |
| **Project Dashboard** | List simulations, summary metrics, recent activity |
| **Archive/Delete** | Soft delete with recovery option |

### 4.3 Simulation Wizard

Recreate existing Streamlit wizard functionality in React:

#### Step 1: Setup Configuration

| Parameter | Type | Description |
|-----------|------|-------------|
| Load Configuration | Multiple modes | Constant, time-windows, seasonal, CSV upload |
| Solar Configuration | File select/upload | Select from library or upload custom profile |
| BESS Parameters | Numeric inputs | Efficiency, SOC limits, cycle limits, container types |
| DG Parameters | Toggle + inputs | Enable/disable, capacity, fuel curve settings |

#### Step 2: Dispatch Rules

| Parameter | Type | Description |
|-----------|------|-------------|
| Template Selection | Dropdown | T0-T6 dispatch templates |
| DG Behavior | Toggles/inputs | Charges BESS, load priority, SOC triggers |
| Time Windows | Time pickers | Night hours, blackout windows |
| Advanced Rules | Toggles | Cycle charging, takeover mode |

#### Step 3: BESS Sizing

| Feature | Description |
|---------|-------------|
| Capacity Range | Min/Max/Step for BESS capacity sweep |
| Duration Classes | Select container types (2-hour, 4-hour) |
| Run Optimization | Execute sizing sweep |
| Results Table | Sortable/filterable results grid |
| Visualizations | Delivery % curves, marginal gain charts |

#### Step 4: Results & Analysis

| Feature | Description |
|---------|-------------|
| Summary Metrics | Key performance indicators |
| Interactive Charts | Plotly-based visualizations |
| Hourly Dispatch View | 8760-hour data explorer |
| Comparison View | Compare multiple configurations |

#### Step 5: Multi-Year Analysis

| Feature | Description |
|---------|-------------|
| Degradation Modeling | Battery capacity fade over years |
| Year-by-Year Results | Annual performance metrics |
| Lifetime Economics | NPV, payback period (if applicable) |

#### Step 6: Green Energy Analysis

| Feature | Description |
|---------|-------------|
| 4D Optimization | Solar × BESS × Container × DG sweep |
| Range Configuration | Min/Max/Step for each dimension |
| Green Energy Targets | Minimum green %, maximum wastage % |
| Viability Filtering | Filter configs meeting targets |
| Heatmap Visualizations | Green % and Wastage % by Solar × BESS |
| Hourly Export | Generate 8760-hour dispatch for selected config |

### 4.4 Data Management

| Feature | Description |
|---------|-------------|
| **Save Simulation** | Persist current results with user-defined name |
| **Load Simulation** | Retrieve saved simulation into cache |
| **Rename Simulation** | Edit display name |
| **Delete Simulation** | Remove saved simulation |
| **Export CSV** | Download results as CSV |
| **Export Excel** | Download results as formatted Excel |
| **Export Hourly Data** | Download 8760-hour dispatch sheet |

### 4.5 Admin Panel

| Feature | Description |
|---------|-------------|
| **User Management** | Create, edit, disable, delete users |
| **Role Assignment** | Assign roles to users |
| **Project Management** | View all projects, reassign ownership |
| **Audit Logs** | View user activity, filter by user/action/date |
| **System Settings** | Configure global defaults, feature toggles |

### 4.6 Management Dashboard

| Feature | Description |
|---------|-------------|
| **Project Overview** | Summary cards for all accessible projects |
| **Key Metrics** | Aggregated statistics across simulations |
| **Recent Activity** | Timeline of recent simulations |
| **AI Insights** | AI-generated summary of findings |

### 4.7 AI Features (Phase 2)

#### 4.7.1 AI Chat Interface

| Feature | Description |
|---------|-------------|
| **Contextual Chat** | Chat within project/simulation context |
| **Conversation History** | Persistent chat history |
| **Privacy Toggle** | Switch between local and cloud AI |

#### 4.7.2 AI Capabilities

| Capability | Description | Example Query |
|------------|-------------|---------------|
| **Natural Language Queries** | Query results using plain English | "Show configs with >80% green energy and <15% wastage" |
| **Result Interpretation** | AI explains what results mean | "Why does this config have low delivery?" |
| **Scenario Recommendations** | AI suggests optimal configurations | "What's the best config for 90% delivery with minimal DG?" |
| **Comparative Analysis** | AI compares configurations | "Compare the top 3 viable configs" |
| **Report Generation** | AI writes executive summaries | "Generate a summary report for management" |
| **Anomaly Detection** | AI flags unusual patterns | "Are there any unexpected results in this simulation?" |

#### 4.7.3 AI Architecture

| Component | Description |
|-----------|-------------|
| **Local AI** | Ollama with LLaMA/Mistral for privacy-sensitive queries |
| **Cloud AI** | OpenAI GPT-4 / Anthropic Claude for complex analysis |
| **Privacy Controls** | User selects per-query or sets default preference |
| **Context Injection** | AI receives metadata.json + relevant Parquet data |

---

## 5. Non-Functional Requirements

### 5.1 Performance

| Metric | Target |
|--------|--------|
| **Page Load Time** | < 2 seconds |
| **API Response Time** | < 500ms for standard queries |
| **Simulation Speed** | < 50ms per configuration (single simulation) |
| **Large Optimization** | 2000 configs in < 2 minutes |
| **Concurrent Users** | Support 10+ simultaneous users |

### 5.2 Security

| Requirement | Implementation |
|-------------|----------------|
| **HTTPS Only** | All traffic encrypted (via Cloudflare) |
| **Password Hashing** | bcrypt with appropriate cost factor |
| **JWT Security** | Short-lived access tokens, secure refresh flow |
| **Input Validation** | Server-side validation on all inputs |
| **SQL Injection Prevention** | Parameterized queries / ORM |
| **XSS Prevention** | React's built-in escaping + CSP headers |
| **CORS** | Restrict to known origins |
| **Rate Limiting** | Prevent brute force attacks |

### 5.3 Reliability

| Requirement | Implementation |
|-------------|----------------|
| **Data Backup** | PostgreSQL daily backup (automated script) |
| **File Backup** | Simulation files included in backup |
| **Error Handling** | Graceful error messages, no stack traces to users |
| **Logging** | Structured logging for debugging |
| **Health Checks** | Docker health checks for all services |

### 5.4 Usability

| Requirement | Description |
|-------------|-------------|
| **Responsive Design** | Works on desktop, tablet (mobile not required) |
| **Loading States** | Skeleton loaders, progress indicators |
| **Error Messages** | User-friendly, actionable error messages |
| **Form Validation** | Real-time validation feedback |
| **Keyboard Navigation** | Accessible via keyboard |

### 5.5 Maintainability

| Requirement | Description |
|-------------|-------------|
| **Code Quality** | ESLint (frontend), Ruff/Black (backend) |
| **Type Safety** | TypeScript (frontend), Type hints (backend) |
| **Test Coverage** | Minimum 70% coverage |
| **Documentation** | Inline comments for complex logic |
| **Modular Architecture** | Separation of concerns, reusable components |

---

## 6. Delivery Phases

### 6.1 Phase 1: Full Application

**Duration:** To be estimated by contractor

**Scope:** Complete functional application without AI features

#### 6.1.1 Infrastructure Deliverables

- [ ] Docker Compose configuration (all services)
- [ ] PostgreSQL schema and migrations
- [ ] Nginx configuration
- [ ] Cloudflare Tunnel setup guide
- [ ] Environment configuration management
- [ ] Backup scripts

#### 6.1.2 Backend Deliverables

- [ ] FastAPI application structure
- [ ] JWT authentication system
- [ ] User management API (CRUD)
- [ ] Project management API (CRUD)
- [ ] Simulation engine API (port existing Python logic)
- [ ] File storage management (Parquet + JSON)
- [ ] Export API (CSV, Excel)
- [ ] Audit logging

#### 6.1.3 Frontend Deliverables

- [ ] React application structure (TypeScript)
- [ ] Authentication UI (login, password reset)
- [ ] Project list and dashboard
- [ ] Simulation wizard (all 6 steps)
- [ ] Results visualization (all charts)
- [ ] Data management UI (save, load, export)
- [ ] Admin panel
- [ ] Management dashboard

#### 6.1.4 Phase 1 Acceptance Criteria

- [ ] All user roles can log in and access appropriate features
- [ ] Complete simulation workflow functional (Steps 1-6)
- [ ] Results match existing Streamlit application
- [ ] Save/load simulations working correctly
- [ ] Export to CSV/Excel functional
- [ ] Admin can manage users and view audit logs
- [ ] Application runs in Docker on local machine
- [ ] Accessible via Cloudflare Tunnel from internet
- [ ] 70%+ test coverage

---

### 6.2 Phase 2: AI Integration & Polish

**Duration:** To be estimated by contractor

**Scope:** AI features, performance optimization, final polish

#### 6.2.1 AI Deliverables

- [ ] AI service integration (local Ollama + cloud API)
- [ ] Chat interface UI
- [ ] Conversation history storage
- [ ] Privacy toggle (local vs cloud)
- [ ] Natural language query processing
- [ ] Result interpretation prompts
- [ ] Scenario recommendation logic
- [ ] Report generation templates
- [ ] Anomaly detection logic

#### 6.2.2 Polish Deliverables

- [ ] Performance optimization (lazy loading, caching)
- [ ] UI/UX refinements (animations, transitions)
- [ ] Error handling improvements
- [ ] Loading states and feedback
- [ ] Responsive design adjustments

#### 6.2.3 Documentation Deliverables

- [ ] API documentation (OpenAPI/Swagger)
- [ ] Deployment guide
- [ ] User guide
- [ ] Administrator guide

#### 6.2.4 Phase 2 Acceptance Criteria

- [ ] AI chat functional with both local and cloud providers
- [ ] All 6 AI capabilities working as specified
- [ ] Privacy toggle correctly routes queries
- [ ] Page load times < 2 seconds
- [ ] All documentation complete
- [ ] Final test coverage maintained at 70%+

---

## 7. Deliverables & Acceptance Criteria

### 7.1 Code Deliverables

| Deliverable | Format |
|-------------|--------|
| **Source Code** | GitHub repository |
| **Frontend** | React/TypeScript application |
| **Backend** | FastAPI/Python application |
| **Database** | PostgreSQL migrations/schema |
| **Infrastructure** | Docker Compose files |
| **Tests** | Unit tests, integration tests |

### 7.2 Documentation Deliverables

| Document | Contents |
|----------|----------|
| **API Documentation** | OpenAPI spec, endpoint descriptions, examples |
| **Deployment Guide** | Step-by-step setup instructions, environment variables, troubleshooting |
| **User Guide** | Feature walkthroughs, screenshots, FAQ |
| **Administrator Guide** | User management, backup procedures, monitoring |

### 7.3 Source Control Requirements

| Requirement | Description |
|-------------|-------------|
| **Repository** | GitHub (private repository) |
| **Branching** | Feature branches, pull requests |
| **Commits** | Descriptive commit messages |
| **Code Review** | All code reviewed before merge |
| **CI/CD** | GitHub Actions for tests and builds |

### 7.4 Testing Requirements

| Test Type | Coverage | Description |
|-----------|----------|-------------|
| **Unit Tests** | 70%+ | Individual functions and components |
| **Integration Tests** | Key flows | API endpoints, database operations |
| **E2E Tests** | Critical paths | Login, simulation workflow, export |

### 7.5 Handoff Requirements

| Item | Description |
|------|-------------|
| **Code Access** | Full repository access transferred |
| **Environment Variables** | Documented and securely transferred |
| **Admin Credentials** | Initial admin account credentials |
| **Knowledge Transfer** | 2-hour walkthrough session (recommended) |

---

## 8. Reference Materials

### 8.1 Existing Codebase

The following files from the existing Streamlit prototype are provided as reference:

| File/Directory | Purpose | Reuse Recommendation |
|----------------|---------|----------------------|
| `/src/dispatch_engine.py` | Core simulation logic | Port to FastAPI service |
| `/src/green_energy_optimizer.py` | 4D optimization sweep | Port to FastAPI service |
| `/src/config.py` | Default configuration | Reference for defaults |
| `/src/data_loader.py` | Solar profile management | Port to FastAPI service |
| `/pages/Step1_Setup.py` - `Step6_*.py` | UI workflow reference | Reference for React rebuild |
| `/utils/metrics.py` | Metrics calculations | Port to FastAPI service |

### 8.2 Domain Knowledge

Key BESS simulation concepts documented in `CLAUDE.md`:

- Binary delivery constraint (25 MW or 0 MW)
- Solar-only charging (battery never charges from grid)
- Cycle limit enforcement (max 2.0 cycles/day)
- SOC operational range (5% - 95%)
- State machine behavior and cycle counting
- Efficiency calculations (87% round-trip)
- Dispatch templates (T0-T6)

### 8.3 Technical References

| Resource | URL |
|----------|-----|
| FastAPI Documentation | <https://fastapi.tiangolo.com/> |
| React Documentation | <https://react.dev/> |
| PostgreSQL Documentation | <https://www.postgresql.org/docs/> |
| Docker Compose | <https://docs.docker.com/compose/> |
| Cloudflare Tunnel | <https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/> |
| Plotly.js | <https://plotly.com/javascript/> |
| Parquet Format | <https://parquet.apache.org/> |

---

## Appendix A: Decision Log

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | Frontend | React | Professional UI, large ecosystem, talent availability |
| 2 | Backend | FastAPI | Performance, Python ecosystem, reuse existing code |
| 3 | Database | PostgreSQL | Industry standard, JSON support, reliability |
| 4 | Admin Panel | Custom React | Consistent UI, full control |
| 5 | Hosting | Desktop + Docker + Cloudflare | Cost-effective Level 1, easy migration to cloud |
| 6 | Authentication | Custom JWT | Self-contained, no external dependencies |
| 7 | AI Provider | Hybrid (local + cloud) | Privacy control, flexibility |
| 8 | User Roles | Admin, Analyst, Viewer, Management | Covers all user types |
| 9 | Multi-project | Yes | Organize by client/site |
| 10 | Data Storage | Session cache + Parquet/JSON | Performance + selective persistence |
| 11 | Cache Expiration | Session-based | Simple, predictable |
| 12 | File Format | Parquet + JSON | Compact results + readable metadata |
| 13 | Deployment | Docker Compose | Consistent, portable |
| 14 | Source Control | GitHub | Industry standard |
| 15 | Documentation | Standard | API docs + guides |
| 16 | Testing | Standard (70%+) | Quality balance |
| 17 | Delivery | 2 Phases | Risk reduction, early validation |

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **BESS** | Battery Energy Storage System |
| **SOC** | State of Charge (battery level as percentage) |
| **DG** | Diesel Generator |
| **MWh** | Megawatt-hour (energy capacity) |
| **MW** | Megawatt (power capacity) |
| **MWp** | Megawatt-peak (solar capacity) |
| **Dispatch** | Allocation of energy resources to meet load |
| **Green Energy** | Energy delivered from solar + battery (no DG) |
| **Wastage** | Solar energy curtailed (not used or stored) |
| **Cycle** | One full charge + discharge of battery |
| **C-Rate** | Charge/discharge rate relative to capacity |
| **Round-trip Efficiency** | Energy out / Energy in for battery |

---

## Appendix C: Contact Information

| Role | Contact |
|------|---------|
| **Project Owner** | [To be filled] |
| **Technical Contact** | [To be filled] |
| **Email** | [To be filled] |

---

*End of Requirements Document*
