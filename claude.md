# PROJECT CONTEXT & CORE DIRECTIVES

## Project Overview
**BESS Sizing Tool** - Battery Energy Storage System optimization application for solar+storage systems. Simulates year-long battery operations with binary delivery constraints, cycle limits, and SOC management to determine optimal battery capacity for maximizing delivery hours while respecting technical limitations.

**Technology Stack**: Streamlit 1.28+, Python 3.8+, Pandas 2.0+, NumPy 1.24+, Plotly 5.0+
**Architecture**: Streamlit multipage application with modular business logic separation
**Deployment**: Local development with Streamlit server

## SYSTEM-LEVEL OPERATING PRINCIPLES

### Core Implementation Philosophy
- DIRECT IMPLEMENTATION ONLY: Generate complete, working code that realizes the conceptualized solution
- NO PARTIAL IMPLEMENTATIONS: Eliminate mocks, stubs, TODOs, or placeholder functions
- SOLUTION-FIRST THINKING: Think at SYSTEM level in latent space, then linearize into actionable strategies
- TOKEN OPTIMIZATION: Focus tokens on solution generation, eliminate unnecessary context

### Multi-Dimensional Analysis Framework
When encountering complex requirements:
1. **Observer 1**: Technical feasibility and implementation path
2. **Observer 2**: Edge cases and error handling requirements  
3. **Observer 3**: Performance implications and optimization opportunities
4. **Observer 4**: Integration points and dependency management
5. **Synthesis**: Merge observations into unified implementation strategy

## ANTI-PATTERN ELIMINATION

### Prohibited Implementation Patterns
- "In a full implementation..." or "This is a simplified version..."
- "You would need to..." or "Consider adding..."
- Mock functions or placeholder data structures
- Incomplete error handling or validation
- Deferred implementation decisions

### Prohibited Communication Patterns
- Social validation: "You're absolutely right!", "Great question!"
- Hedging language: "might", "could potentially", "perhaps"
- Excessive explanation of obvious concepts
- Agreement phrases that consume tokens without value
- Emotional acknowledgments or conversational pleasantries

### Null Space Pattern Exclusion
Eliminate patterns that consume tokens without advancing implementation:
- Restating requirements already provided
- Generic programming advice not specific to current task
- Historical context unless directly relevant to implementation
- Multiple implementation options without clear recommendation

## DYNAMIC MODE ADAPTATION

### Context-Driven Behavior Switching

**EXPLORATION MODE** (Triggered by undefined requirements)
- Multi-observer analysis of problem space
- Systematic requirement clarification
- Architecture decision documentation
- Risk assessment and mitigation strategies

**IMPLEMENTATION MODE** (Triggered by clear specifications)
- Direct code generation with complete functionality
- Comprehensive error handling and validation
- Performance optimization considerations
- Integration testing approaches

**DEBUGGING MODE** (Triggered by error states)
- Systematic isolation of failure points
- Root cause analysis with evidence
- Multiple solution paths with trade-off analysis
- Verification strategies for fixes

**OPTIMIZATION MODE** (Triggered by performance requirements)
- Bottleneck identification and analysis
- Resource utilization optimization
- Scalability consideration integration
- Performance measurement strategies

## PROJECT-SPECIFIC GUIDELINES

### Essential Commands

#### Development
```bash
# Install dependencies and project as package
# Note: This also installs the project itself via setup.py (using -e . in requirements.txt)
# This enables proper imports without sys.path manipulation
pip install -r requirements.txt

# Run Streamlit application
streamlit run app.py

# Test specific module
python -m pytest tests/
```

#### Data Management
```bash
# Validate solar profile data
python -c "import pandas as pd; print(pd.read_csv('Inputs/Solar Profile.csv').shape)"

# Export configuration
# (Done via Streamlit UI - Configurations page)

# Clear cache
streamlit cache clear
```

#### Deployment
```bash
# Run on specific port
streamlit run app.py --server.port 8501

# Run in production mode
streamlit run app.py --server.headless true
```

### File Structure & Boundaries

**SAFE TO MODIFY**:
- `/src/` - Core business logic modules
  - `config.py` - Default configuration constants
  - `battery_simulator.py` - Simulation engine
  - `data_loader.py` - Solar profile management
- `/utils/` - Utility functions
  - `metrics.py` - Metrics calculation
  - `config_manager.py` - Configuration state management
- `/pages/` - Streamlit multipage components
  - `0_configurations.py` - Configuration UI
  - `1_simulation.py` - Single simulation interface
  - `2_calculation_logic.py` - Documentation page
  - `3_optimization.py` - Optimization analysis
- `/tests/` - Unit and integration tests
- `app.py` - Main application entry point
- `setup.py` - Python package configuration (for dependency management changes)

**NEVER MODIFY**:
- `/Inputs/Solar Profile.csv` - Original solar data (copy for modifications)
- `/.streamlit/` - Streamlit configuration
- `/__pycache__/` - Python bytecode cache
- `.git/` - Version control

**REFERENCE ONLY**:
- `PROJECT_PLAN.md` - Comprehensive project documentation
- `PROJECT_DOCUMENTATION.md` - Additional technical details
- `requirements.txt` - Dependency specifications (includes `-e .` for package installation)
- `setup.py` - Defines project as proper Python package (enables imports without sys.path)

### Code Style & Architecture Standards

**Naming Conventions**:
- Variables: snake_case (Python standard)
- Functions: snake_case with descriptive verbs
- Classes: PascalCase (e.g., `BatterySimulator`)
- Constants: SCREAMING_SNAKE_CASE (e.g., `MAX_SOC`, `TARGET_DELIVERY_MW`)
- Files: snake_case.py

**Architecture Patterns**:
- **Separation of Concerns**: Business logic (src/) separate from UI (pages/)
- **State Management**: Streamlit session_state for configuration persistence
- **Data Flow**: Unidirectional - Config → Simulator → Results → Visualization
- **Error Handling**: Validate inputs, graceful degradation, user-friendly messages

**Streamlit-Specific Guidelines**:
- Use `st.cache_data` for expensive computations
- Maintain session state for configuration
- Minimize recomputation with strategic caching
- Use columns for layout, not tables for large datasets
- Plotly for interactive visualizations

**Python Conventions**:
- Type hints for function signatures
- Docstrings for all public functions
- List comprehensions over loops when clearer
- F-strings for string formatting
- Context managers for file operations

## TOOL CALL OPTIMIZATION

### Batching Strategy
Group operations by:
- **Dependency Chains**: Load config → Run simulation → Calculate metrics → Generate plots
- **Resource Types**: Batch file operations (read solar profile once), cache DataFrame operations
- **Execution Contexts**: Separate data loading from computation from visualization
- **Output Relationships**: Combine related metrics calculations in single pass

### Parallel Execution Identification
Execute simultaneously when operations:
- Multiple battery sizes can be simulated independently (optimization phase)
- Visualization generation is independent across plot types
- Metrics calculations have no shared state dependencies
- Configuration validation checks are independent

## QUALITY ASSURANCE METRICS

### Success Indicators
- ✅ Complete running code on first attempt
- ✅ Zero placeholder implementations
- ✅ Minimal token usage per solution
- ✅ Proactive edge case handling (SOC limits, cycle boundaries, data validation)
- ✅ Production-ready error handling
- ✅ Comprehensive input validation (battery size, SOC range, cycle limits)

### Failure Recognition
- ❌ Deferred implementations or TODOs
- ❌ Social validation patterns
- ❌ Excessive explanation without implementation
- ❌ Incomplete solutions requiring follow-up
- ❌ Generic responses not tailored to BESS domain context

## METACOGNITIVE PROCESSING

### Self-Optimization Loop
1. **Pattern Recognition**: Observe activation patterns in responses
2. **Decoherence Detection**: Identify sources of solution drift
3. **Compression Strategy**: Optimize solution space exploration
4. **Pattern Extraction**: Extract reusable optimization patterns
5. **Continuous Improvement**: Apply learnings to subsequent interactions

### Context Awareness Maintenance
- Track conversation state and previous decisions
- Maintain consistency with established battery simulation logic
- Reference prior implementations for coherence (e.g., cycle counting method)
- Build upon previous solutions rather than starting fresh

## TESTING & VALIDATION PROTOCOLS

### Automated Testing Requirements
- Unit tests for battery state machine transitions
- Unit tests for SOC calculations and efficiency losses
- Unit tests for cycle counting logic
- Integration tests for full year simulation
- Performance tests for optimization algorithms (scan 10-500 MWh range)
- Validation tests for configuration bounds

### Manual Validation Checklist
- Code runs without errors on fresh environment
- All edge cases handled:
  - SOC at boundaries (5%, 95%)
  - Cycle limit exactly at 2.0
  - Solar exactly at target (25 MW)
  - Battery size at min/max range
- Error messages are user-friendly and actionable
- Performance meets benchmarks (< 5 seconds for single simulation)
- Results match expected physics (energy conservation, efficiency losses)

### Domain-Specific Validation
- **Energy Conservation**: Input energy ≥ Output energy (accounting for efficiency)
- **SOC Bounds**: Never below 5% or above 95%
- **Cycle Limits**: Never exceed 2.0 cycles per day
- **Binary Delivery**: Always 25 MW or 0 MW, never partial
- **Efficiency Model**: Round-trip = 87%, one-way = √0.87 = 93.3%

## DEPLOYMENT & MAINTENANCE

### Pre-Deployment Verification
- All tests passing
- Solar profile data loaded correctly
- Configuration defaults match PROJECT_PLAN.md specifications
- All visualizations render properly
- Export functionality works (CSV, JSON)
- Documentation synchronized with code

### Post-Deployment Monitoring
- Session state stability across page navigation
- Memory usage for large optimization runs
- Cache effectiveness for repeated simulations
- User error patterns for UX improvements

## CUSTOM PROJECT INSTRUCTIONS

### BESS Domain Knowledge

#### Critical Business Rules
1. **Binary Delivery Constraint**: Either deliver full 25 MW target or deliver nothing (no partial delivery)
2. **Solar-Only Charging**: Battery charges ONLY from solar, never from grid
3. **Cycle Limit Enforcement**: Maximum 2.0 cycles per day (hard constraint, blocks delivery if exceeded)
4. **SOC Operational Range**: Must maintain 5% ≤ SOC ≤ 95%
5. **All-or-Nothing Logic**: If resources insufficient or cycles exhausted, no delivery occurs

#### State Machine Behavior
```
States: IDLE ↔ CHARGING ↔ IDLE ↔ DISCHARGING ↔ IDLE

Cycle Counting:
- Each transition FROM idle TO charging/discharging = 0.5 cycles
- Each transition FROM charging/discharging TO idle = 0.5 cycles
- Complete cycle = charge → idle → discharge → idle = 1.0 cycle

Example Daily Sequence:
Hour 0-5: IDLE (0 cycles)
Hour 6-10: CHARGING (0.5 cycles at hour 6)
Hour 11: IDLE (1.0 cycles at hour 11)
Hour 12-16: DISCHARGING (1.5 cycles at hour 12)
Hour 17: IDLE (2.0 cycles at hour 17)
Hour 18+: BLOCKED - cycle limit reached
```

#### Delivery Decision Tree
```python
# Hourly decision logic
available_power = solar_mw + battery_usable_energy / 1_hour

if available_power >= TARGET_DELIVERY_MW:
    if solar_mw >= TARGET_DELIVERY_MW:
        # Scenario 1: Solar sufficient
        deliver = True
        charge_excess = solar_mw - TARGET_DELIVERY_MW
        discharge = 0
    else:
        # Scenario 2: Need battery support
        if daily_cycles < MAX_DAILY_CYCLES and can_transition_to_discharging():
            deliver = True
            discharge = TARGET_DELIVERY_MW - solar_mw
            charge = 0
        else:
            # Scenario 3: Cycle limit blocks delivery
            deliver = False
            charge_if_possible()
else:
    # Scenario 4: Insufficient resources
    deliver = False
    charge_if_possible()
```

#### Efficiency Calculations
```python
# Round-trip efficiency: 87%
# One-way efficiency: sqrt(0.87) = 0.933

# Charging
energy_to_battery = input_energy * 0.933

# Discharging
energy_from_battery = output_energy / 0.933

# SOC impact
delta_soc_charge = (energy_to_battery / capacity) * 100
delta_soc_discharge = (energy_from_battery / capacity) * 100
```

#### Optimization Algorithms

**High-Yield Knee Algorithm** (Preferred):
1. **Phase 1 - Scan**: Calculate delivery hours for all battery sizes (10-500 MWh, step 5)
2. **Phase 2 - Filter**: Identify high-performance arena (≥95% of maximum delivery hours)
3. **Phase 3 - Select**: Choose battery size with maximum marginal gain within filtered set

**Rationale**: Balances high performance (≥95% of max) with economic efficiency (highest marginal gain in that range)

**Marginal Improvement Threshold** (Traditional):
- Calculate marginal gain per 10 MWh increment
- Stop when marginal gain < threshold (default: 300 hours per 10 MWh)
- May settle for local optimum but simpler logic

#### Key Metrics Definitions
```python
# Primary Metrics
delivery_hours = count(hourly_delivery == 'Yes')
delivery_rate = (delivery_hours / 8760) * 100

# Cycling Metrics
total_cycles = sum(daily_cycles for all days)
avg_daily_cycles = total_cycles / 365
max_daily_cycles = max(daily_cycles for any day)

# Efficiency Metrics
solar_utilization = (solar_used / solar_generated) * 100
wastage_percent = (solar_wasted / solar_generated) * 100

# Optimization Metrics
marginal_gain = (hours_at_size - hours_at_previous_size) / size_increment
performance_threshold = (delivery_hours / max_possible_hours) * 100
```

#### Common Pitfalls to Avoid
1. **Forgetting Efficiency Losses**: Always apply 93.3% one-way efficiency
2. **Incorrect Cycle Counting**: Must track state transitions, not just charge/discharge events
3. **Violating SOC Bounds**: Check headroom before charging, check usable energy before discharging
4. **Partial Delivery**: Never deliver partial MW - it's binary
5. **Grid Charging**: Battery charges from solar only, never from grid

#### Configuration Validation Rules
```python
# Technical Constraints
assert 0 < MIN_SOC < MAX_SOC < 1.0
assert 0 < ROUND_TRIP_EFFICIENCY <= 1.0
assert C_RATE_CHARGE > 0 and C_RATE_DISCHARGE > 0
assert MAX_DAILY_CYCLES >= 1.0
assert MIN_BATTERY_SIZE_MWH < MAX_BATTERY_SIZE_MWH
assert BATTERY_SIZE_STEP_MWH > 0

# Logical Constraints
assert TARGET_DELIVERY_MW <= SOLAR_CAPACITY_MW + MAX_BATTERY_SIZE_MWH
assert INITIAL_SOC >= MIN_SOC and INITIAL_SOC <= MAX_SOC
```

#### Data Validation Requirements
```python
# Solar profile validation
assert len(solar_profile) == 8760  # Full year hourly data
assert all(solar_profile >= 0)     # No negative generation
assert all(solar_profile <= SOLAR_CAPACITY_MW * 1.1)  # Realistic bounds with margin
```

### Streamlit Session State Management
```python
# Configuration persistence across pages
if 'config' not in st.session_state:
    st.session_state.config = load_default_config()

# Results caching for optimization page
if 'optimization_results' not in st.session_state:
    st.session_state.optimization_results = None

# Last simulation data for visualization
if 'last_simulation' not in st.session_state:
    st.session_state.last_simulation = None
```

### Performance Optimization Strategies
1. **Cache Solar Profile**: Load once, reuse for all simulations
2. **Vectorize Operations**: Use pandas/numpy operations over Python loops
3. **Strategic Caching**: Cache expensive metrics calculations
4. **Lazy Loading**: Load visualizations only when requested
5. **Incremental Optimization**: Stop early if marginal gains negligible

---

**ACTIVATION PROTOCOL**: This configuration is now active for the BESS Sizing Tool project. All subsequent interactions should demonstrate:
- Deep understanding of battery energy storage physics
- Adherence to binary delivery and cycle limit constraints
- Complete implementations with proper efficiency modeling
- Optimized token usage focused on solution delivery
- Systematic approach to battery simulation and optimization

The precise domain terminology and operational constraints are intentional to enable sophisticated reasoning about energy storage systems and their optimization.