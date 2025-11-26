# BESS Sizing Tool - Complete Project Plan & Documentation

> **Version 1.1.1** (2025-11-24) - Updated with Python 3.13 compatibility and deployment fixes
>
> See [CHANGELOG.md](CHANGELOG.md) for version history and recent updates.

## 📋 Executive Summary

The Battery Energy Storage System (BESS) Sizing Tool is a comprehensive Streamlit-based application designed to optimize battery storage sizing for solar energy systems. The tool simulates year-long battery operations, enforces operational constraints, and provides advanced optimization algorithms to determine the ideal battery capacity for maximizing delivery hours while respecting technical limitations.

**Recent Updates (v1.1.1):**

- Python 3.13 compatibility with updated dependencies
- Fixed Streamlit Cloud deployment errors (numpy 2.1.3, streamlit 1.39.0)
- Removed editable install from requirements.txt for cloud compatibility
- Updated all packages to latest stable versions

**Previous (v1.1.0):**
- Professional logging framework, pinned dependencies, enhanced package structure

---

## 🎯 Project Objectives

### Primary Goals
1. **Optimize Battery Sizing**: Determine optimal battery capacity for solar+storage systems
2. **Binary Delivery Constraint**: Ensure all-or-nothing delivery of 25 MW target power
3. **Maximize Delivery Hours**: Find battery size that maximizes hours of successful delivery
4. **Respect Operational Limits**: Enforce daily cycle limits and State of Charge (SOC) constraints
5. **Provide Actionable Insights**: Generate detailed metrics and visualizations for decision-making

### Key Requirements
- Binary delivery: Either deliver full 25 MW or nothing
- Battery charges ONLY from solar (no grid charging)
- Maximum 2 cycles per day limit
- SOC operational range: 5% - 95%
- Track degradation based on cycling

---

## 🏗️ System Architecture

### Technology Stack
```
Frontend:        Streamlit 1.39.0 (pinned)
Backend:         Python 3.11+ (3.13 recommended)
Data Processing: Pandas 2.2.3 (pinned), NumPy 2.1.3 (pinned, Python 3.13 compatible)
Visualization:   Plotly 5.24.1 (pinned)
Logging:         Python logging module (built-in)
```

**Note:** All dependencies are pinned to exact versions in `requirements.txt` for reproducible deployments and full Python 3.13 compatibility (v1.1.1+).

### Application Structure
```
BESS-22-nov/
│
├── app.py                     # Main application entry point
├── setup.py                   # Python package configuration (enables proper imports)
├── requirements.txt           # Python dependencies (pinned versions, Python 3.13 compatible)
├── CHANGELOG.md              # Version history and changes (NEW in v1.1.0)
├── BUG_REPORT_ANALYSIS.md    # Detailed bug tracking and fixes
├── PROJECT_PLAN.md           # This document
│
├── src/                      # Core business logic (installed as package)
│   ├── __init__.py          # Package exports (enhanced in v1.1.0)
│   ├── config.py            # Default configuration constants
│   ├── battery_simulator.py # Battery operation simulation engine
│   └── data_loader.py       # Solar profile data management (with logging)
│
├── utils/                    # Utility functions (installed as package)
│   ├── __init__.py          # Package exports (enhanced in v1.1.0)
│   ├── logger.py            # Centralized logging framework (NEW in v1.1.0)
│   ├── metrics.py           # Metrics calculation and analysis
│   ├── config_manager.py   # Configuration state management
│   └── validators.py        # Configuration validation utilities
│
├── pages/                    # Streamlit multipage app
│   ├── 0_configurations.py  # Configuration management page
│   ├── 1_simulation.py      # Single battery simulation
│   ├── 2_calculation_logic.py # Documentation page
│   └── 3_optimization.py    # Advanced optimization analysis
│
└── Inputs/                   # Data inputs
    └── Solar Profile.csv     # Hourly solar generation data

```

**Package Structure Notes:**
- `setup.py` defines the project as a proper Python package
- `src/` and `utils/` are installed as importable packages
- All pages can import from `src` and `utils` naturally (no sys.path manipulation)
- Compatible with both local development and cloud deployment

---

## 📊 Core Features

### 1. Configuration Management
**Page**: `0_configurations.py`

#### Configurable Parameters:
- **Project Parameters**
  - Target Delivery: 25 MW (adjustable)
  - Solar Capacity: 67 MW (adjustable)

- **Battery Technical Parameters**
  - SOC Limits: Min 5%, Max 95%
  - Round-trip Efficiency: 87%
  - C-rates: 1.0 for both charge and discharge
  - Initial SOC: 50%

- **Operational Parameters**
  - Max Daily Cycles: 2.0
  - Degradation: 0.15% per cycle

- **Optimization Parameters**
  - Battery Size Range: 10-500 MWh
  - Step Size: 5 MWh
  - Marginal Improvement Threshold: 300 hours/10MWh

#### Features:
- Real-time configuration updates
- Session persistence
- Configuration export/import (JSON)
- Validation warnings for invalid settings
- Reset to defaults option

### 2. Battery Simulation Engine
**File**: `src/battery_simulator.py`

#### Core Algorithm:
```python
For each hour in year:
    1. Check available resources (Solar + Battery)
    2. Determine if can deliver target (25 MW)
    3. Check cycle limits if battery needed
    4. Execute delivery or charging decision
    5. Track state transitions and cycles
    6. Update SOC and metrics
```

#### State Machine:
```
States: IDLE → CHARGING → IDLE → DISCHARGING → IDLE
Cycles: Each transition to/from charging or discharging = 0.5 cycles
```

#### Cycle Tracking Method:
- **State Transition Based**: Each state change counts as 0.5 cycles
- **Daily Limit Enforcement**: Maximum 2.0 cycles per day
- **Impact**: Delivery capability blocked if cycle limit reached

### 3. Optimization Algorithms

#### A. High-Yield Knee Algorithm
**Innovative three-phase approach:**

```python
Phase 1 - Scan: Calculate marginal gains for all battery sizes
Phase 2 - Filter: Identify high-performance arena (≥95% of max)
Phase 3 - Select: Choose maximum marginal gain in filtered set
```

**Advantages:**
- Avoids local optima
- Balances performance and efficiency
- Considers economic viability

#### B. Marginal Improvement Threshold
**Traditional approach:**
- Stops when marginal improvement < threshold
- May settle for local optimum
- Simpler but less sophisticated

### 4. Data Visualization
**Page**: `3_optimization.py`

#### Interactive Visualizations:
1. **Delivery Hours vs Battery Size**: Performance curve
2. **Marginal Gains Analysis**: Efficiency per MWh added
3. **Performance Threshold**: High-performance zone identification
4. **Cost-Benefit Curve**: Value per MWh analysis

#### Metrics Dashboard:
- Optimal battery size
- Total delivery hours
- Delivery rate percentage
- Marginal gain at optimal point
- Degradation analysis
- Cycle statistics

---

## 💻 Technical Implementation

### 1. Binary Delivery Logic
```python
# Delivery decision tree
if (solar + battery_available) >= 25 MW:
    if solar >= 25 MW:
        → Deliver + Charge excess
    else:
        if can_cycle():
            → Deliver + Discharge deficit
        else:
            → Cannot deliver (cycle limit)
else:
    → Cannot deliver + Charge if possible
```

### 2. Efficiency Calculations
```python
Round-trip Efficiency = 87%
One-way Efficiency = √0.87 = 93.3%

Energy to Battery = Input × 0.933
Energy from Battery = Output × 0.933
```

### 3. SOC Management
```python
Usable Energy = (SOC - 5%) × Capacity
Charge Headroom = (95% - SOC) × Capacity
```

### 4. Hourly Data Structure
```python
{
    'hour': int,                    # Hour of simulation (0-8759)
    'solar_mw': float,              # Solar generation
    'bess_mw': float,               # +ve discharge, -ve charge
    'bess_charge_mwh': float,       # Battery energy content
    'soc_percent': float,           # State of charge %
    'usable_energy_mwh': float,     # Available for discharge
    'committed_mw': float,          # Always 25 MW target
    'deficit_mw': float,            # Shortfall if any
    'delivery': str,                # 'Yes' or 'No'
    'bess_state': str,              # IDLE/CHARGING/DISCHARGING
    'wastage_mwh': float           # Unused solar energy
}
```

---

## 📈 Performance Metrics

### Key Performance Indicators
1. **Delivery Hours**: Total hours meeting 25 MW target
2. **Delivery Rate**: Percentage of year delivering successfully
3. **Total Cycles**: Cumulative battery cycles over year
4. **Average Daily Cycles**: Mean cycles per day
5. **Maximum Daily Cycles**: Peak cycling in any day
6. **Solar Utilization**: Percentage of solar energy used
7. **Wastage**: Unused solar energy percentage
8. **Degradation**: Capacity loss due to cycling

### Optimization Metrics
- **Marginal Gain**: Additional hours per MWh added
- **Performance Threshold**: Percentage of maximum achievable
- **Value per MWh**: Delivery hours per unit capacity

---

## 🚀 Usage Instructions

### Installation
```bash
# Clone repository
git clone [repository-url]
cd "BESS 22 nov"

# Install dependencies and project as package
# Note: This installs all dependencies AND the project itself as an editable package
# This enables proper Python imports without sys.path manipulation
pip install -r requirements.txt

# Run application
streamlit run app.py
```

**Note on Package Installation:**
The project uses a proper Python package structure with `setup.py`. When you run `pip install -r requirements.txt`, it:
1. Installs all required dependencies (streamlit, pandas, numpy, plotly)
2. Installs the project itself as an editable package (via `-e .` in requirements.txt)
3. Makes all imports work naturally without sys.path manipulation

This approach:
- ✅ Works seamlessly on local development
- ✅ Works on Streamlit Cloud deployment
- ✅ Follows Python packaging best practices
- ✅ Enables proper testing and distribution

### Workflow

#### 1. Configure System (Optional)
- Navigate to **Configurations** page
- Adjust parameters as needed
- Save configuration

#### 2. Run Simulation
- Go to **Simulation** page
- Select battery size with slider
- Click "Run Simulation" for single test
- Click "Find Optimal Size" for full analysis

#### 3. Analyze Results
- Visit **Optimization** page
- Results auto-load from simulation
- Compare algorithms (High-Yield Knee vs Marginal)
- Review visualizations and metrics
- Export results as CSV

#### 4. Review Logic
- Check **Calculation Logic** page
- Understand operational scenarios
- Review cycle counting examples

---

## 📁 Data Requirements

### Solar Profile Data

**Required File:** `Inputs/Solar Profile.csv`

The application **requires** a valid solar profile file to run simulations. This file must contain:
- **8760 hourly values** (full year of data)
- **Solar generation in MW** for each hour
- **CSV format** with recognizable column names (e.g., "Solar_Generation_MW", "solar", "generation", "mw")

**Example Format:**
```csv
timestamp,Solar_Generation_MW
01-01-2024 00:00,0
01-01-2024 01:00,0
01-01-2024 06:00,15.2
01-01-2024 12:00,64.8
...
```

**Current Behavior:**
- ✅ Loads from `Inputs/Solar Profile.csv` by default
- ❌ **No synthetic data fallback** - real data is required
- 🛑 Application stops execution if file is missing or invalid
- ⚠️ Clear error messages displayed to users

**Error Handling:**
If the solar profile file is missing or cannot be loaded:
1. User sees clear error message in the UI
2. Instructions provided on how to fix the issue
3. Page execution stops - no simulations can run
4. No silent fallback to synthetic data

### Future Enhancement: Solar Profile Upload

**Status:** Planned for future version
**Priority:** MEDIUM
**Requirement:** User upload capability when default file is unavailable

**Proposed Functionality:**
- File upload widget in Simulation and Optimization pages
- Validation of uploaded files (8760 hours, valid format, no negative values)
- Session state caching of uploaded profiles
- Support for CSV files with various column naming conventions
- Clear upload instructions and file format requirements

**Implementation Notes:**
- Will use Streamlit's `st.file_uploader()` for secure, memory-based uploads
- Uploaded profiles will be validated and cached in session state
- No disk writes required (security benefit)
- Reusable across all pages in same session

**Current Workaround:**
Users must ensure `Inputs/Solar Profile.csv` exists before running the application.

---

## 🔧 Configuration Details

### Default Configuration
```python
# Project Parameters
TARGET_DELIVERY_MW = 25.0
SOLAR_CAPACITY_MW = 67.0

# Battery Technical
MIN_SOC = 0.05 (5%)
MAX_SOC = 0.95 (95%)
ROUND_TRIP_EFFICIENCY = 0.87
C_RATE_CHARGE = 1.0
C_RATE_DISCHARGE = 1.0

# Operational
MAX_DAILY_CYCLES = 2.0
INITIAL_SOC = 0.5 (50%)
DEGRADATION_PER_CYCLE = 0.0015 (0.15%)

# Optimization
MIN_BATTERY_SIZE_MWH = 10
MAX_BATTERY_SIZE_MWH = 500
BATTERY_SIZE_STEP_MWH = 5
MARGINAL_IMPROVEMENT_THRESHOLD = 300
```

---

## 📊 Data Requirements

### Solar Profile Input
- **Format**: CSV file
- **Columns**: Single column with hourly MW values
- **Length**: 8760 hours (full year)
- **Location**: `Inputs/Solar Profile.csv`

### Synthetic Data Fallback
If solar profile unavailable, system generates synthetic data:
- Peak capacity: 67 MW
- Daily pattern with sunrise/sunset
- Random cloud variations
- Seasonal adjustments

---

## 🎯 Optimization Results Interpretation

### High-Yield Knee Selection
**Optimal when:**
- High performance is critical (>95% of max)
- Economic efficiency within high-performance zone matters
- Avoiding oversizing is important

**Example Result:**
```
Optimal Size: 165 MWh
Delivery Hours: 7,884 (90.0%)
Marginal Gain: 45.2 hours/10MWh
Reasoning: Maximum marginal gain in high-performance zone
```

### Marginal Improvement Selection
**Optimal when:**
- Cost is primary concern
- Diminishing returns acceptable
- Simple decision rule preferred

**Example Result:**
```
Optimal Size: 140 MWh
Delivery Hours: 7,650 (87.3%)
Total Cycles: 285
Reasoning: Marginal improvement below 300 hours per 10 MWh
```

---

## 🔒 Constraints & Limitations

### Technical Constraints
1. **Binary Delivery**: No partial delivery allowed
2. **Solar-Only Charging**: No grid charging capability
3. **Cycle Limits**: Hard limit of 2 cycles/day
4. **SOC Bounds**: Must stay within 5-95% range
5. **Efficiency Losses**: 13% round-trip loss

### Modeling Assumptions
1. Perfect forecast (no uncertainty)
2. No auxiliary power consumption
3. Instantaneous state transitions
4. Linear degradation model
5. Fixed efficiency across SOC range

---

## 📈 Future Enhancements

### Planned Features
1. **Economic Analysis**
   - Revenue calculations
   - NPV/IRR analysis
   - Sensitivity analysis

2. **Advanced Algorithms**
   - Machine learning optimization
   - Stochastic optimization
   - Multi-objective optimization

3. **Extended Modeling**
   - Auxiliary consumption
   - Variable efficiency curves
   - Temperature effects
   - Detailed degradation models

4. **Data Integration**
   - Real-time data feeds
   - Weather forecast integration
   - Market price signals

5. **Reporting**
   - Automated report generation
   - Custom KPI dashboards
   - Comparison scenarios

---

## 🛠️ Maintenance & Support

### Code Structure Best Practices
- Modular design with clear separation of concerns
- Configuration isolated from logic
- Reusable utility functions
- Clear state management

### Testing Recommendations
1. Unit tests for battery simulator
2. Integration tests for optimization algorithms
3. Performance tests for large battery ranges
4. Edge case validation

### Documentation
- Inline code comments for complex logic
- Docstrings for all functions
- Type hints where applicable
- This comprehensive project plan

---

## 📝 Version History

### Version 1.1.1 (Current - 2025-11-24)
- Python 3.13 compatibility
- Updated dependencies (numpy 2.1.3, streamlit 1.39.0, pandas 2.2.3, plotly 5.24.1)
- Fixed Streamlit Cloud deployment errors
- Removed editable install from requirements.txt

### Version 1.1.0 (2025-11-23)
- Professional logging framework
- Pinned dependency versions
- Enhanced package structure
- Code quality improvements

### Version 1.0.0 (2024-11-22)
- Full BESS sizing application
- Binary delivery constraint
- Cycle limit enforcement
- High-Yield Knee algorithm
- Configuration management
- Comprehensive visualization
- Session state optimization

---

## 👥 Project Team & Acknowledgments

**Development**: Claude AI Assistant
**Architecture**: Streamlit multipage framework
**Algorithms**: High-Yield Knee (novel), Marginal Improvement (traditional)
**Testing & Validation**: Iterative development with user feedback

---

## 📄 License & Usage Rights

This project is provided as-is for educational and commercial use. Users are encouraged to modify and extend the application to meet specific requirements.

---

*Document Version: 1.1.1*
*Last Updated: November 24, 2025*
*Generated with Claude Code*