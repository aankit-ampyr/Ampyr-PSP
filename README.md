# BESS Sizing Tool 🔋

A comprehensive Battery Energy Storage System (BESS) sizing optimization tool for solar+storage systems.

> **Latest Version: 1.1.1** (2025-11-24)
> Python 3.13 compatible with updated dependencies for Streamlit Cloud deployment.
> See [CHANGELOG.md](CHANGELOG.md) for details.

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
streamlit run app.py
```

Open browser at `http://localhost:8501`

## 📋 Features

- **🔧 Configurable Parameters**: Adjust all system parameters through UI
- **⚡ Real-time Simulation**: Test individual battery sizes instantly
- **🎯 Optimization Algorithms**: High-Yield Knee & Marginal Improvement methods
- **📊 Advanced Visualizations**: Interactive Plotly charts
- **📈 Comprehensive Metrics**: Delivery hours, cycles, degradation tracking
- **💾 Export Capabilities**: Download results as CSV
- **📝 Professional Logging**: Structured logging with timestamps and module identification (NEW in v1.1.0)
- **📦 Package Structure**: Clean imports with proper package initialization (NEW in v1.1.0)

## ✨ What's New in v1.1.1

### Python 3.13 Compatibility & Deployment Fix

- **Python 3.13 Support**: Full compatibility with latest Python version
- **Updated Dependencies**: Modern package versions (NumPy 2.1.3, Streamlit 1.39.0, Pandas 2.2.3, Plotly 5.24.1)
- **Streamlit Cloud Fix**: Resolved deployment errors caused by old numpy incompatibility with Python 3.13
- **Production Ready**: Tested and verified on Streamlit Cloud with Python 3.13.9

### Previous Release (v1.1.0)
- Professional Logging Framework, Pinned Dependencies, Enhanced Package Structure

See [CHANGELOG.md](CHANGELOG.md) for complete release notes.

## 🏗️ Project Structure

```
├── app.py                    # Main entry point
├── setup.py                  # Package configuration
├── requirements.txt          # Dependencies (pinned versions)
├── CHANGELOG.md             # Version history and changes
├── pages/
│   ├── 0_configurations.py  # System configuration
│   ├── 1_simulation.py      # Battery simulation
│   ├── 2_calculation_logic.py # Documentation
│   └── 3_optimization.py    # Optimization analysis
├── src/
│   ├── __init__.py         # Package exports
│   ├── battery_simulator.py # Core simulation engine
│   ├── config.py           # Default configurations
│   └── data_loader.py      # Data management (with logging)
└── utils/
    ├── __init__.py         # Package exports
    ├── logger.py           # Centralized logging (NEW)
    ├── metrics.py          # Metrics calculations
    ├── config_manager.py   # Config state management
    └── validators.py       # Input validation
```

## 🎯 Key Specifications

- **Target Delivery**: 25 MW (binary constraint)
- **Battery Range**: 10-500 MWh
- **SOC Limits**: 5-95%
- **Max Cycles/Day**: 2.0
- **Round-trip Efficiency**: 87%
- **Degradation**: 0.15% per cycle
- **Charging Source**: Solar only (no grid)

## 📊 Optimization Algorithms

### High-Yield Knee Algorithm
Innovative three-phase approach that finds the most efficient battery size within the high-performance zone (≥95% of maximum delivery hours).

### Marginal Improvement Threshold
Traditional method that stops when marginal gains fall below a threshold (default: 300 hours per 10 MWh).

## 🔄 Typical Workflow

1. **Configure** (optional): Adjust system parameters in Configuration page
2. **Simulate**: Run "Find Optimal Size" on Simulation page
3. **Analyze**: Review results on Optimization page with different algorithms
4. **Export**: Download results for further analysis

## 📈 Sample Results

```
Optimal Battery Size: 165 MWh
Delivery Hours: 7,884 / 8,760 (90.0%)
Total Cycles: 298.5
Average Daily Cycles: 0.82
Degradation: 0.448%
```

## 🛠️ Requirements

- **Python 3.11+** (Python 3.13 recommended)
- **Pinned Dependencies** (exact versions for reproducibility):
  - Streamlit 1.39.0
  - Pandas 2.2.3
  - NumPy 2.1.3 (Python 3.13 compatible)
  - Plotly 5.24.1

All dependencies are pinned to exact versions in `requirements.txt` to ensure consistent behavior across deployments and full Python 3.13 compatibility.

## 📄 Documentation

- **[CHANGELOG.md](CHANGELOG.md)** - Version history and recent changes
- **[BUG_REPORT_ANALYSIS.md](BUG_REPORT_ANALYSIS.md)** - Detailed bug tracking and fixes
- **[PROJECT_PLAN.md](PROJECT_PLAN.md)** - Comprehensive technical documentation including:
  - Detailed technical specifications
  - Algorithm explanations
  - Configuration options
  - Usage instructions
  - System architecture

## 🤝 Contributing

Feel free to fork, modify, and submit pull requests. Key areas for contribution:
- Additional optimization algorithms
- Economic analysis features
- Enhanced visualizations
- Performance optimizations

## 📝 License

Open source - free to use and modify for educational and commercial purposes.

---

**Developed with Claude Code** 🤖

*For detailed documentation, see PROJECT_PLAN.md*