# BESS Sizing Tool 🔋

A comprehensive Battery Energy Storage System (BESS) sizing optimization tool for solar+storage systems.

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

## 🏗️ Project Structure

```
├── app.py                    # Main entry point
├── pages/
│   ├── 0_configurations.py  # System configuration
│   ├── 1_simulation.py      # Battery simulation
│   ├── 2_calculation_logic.py # Documentation
│   └── 3_optimization.py    # Optimization analysis
├── src/
│   ├── battery_simulator.py # Core simulation engine
│   ├── config.py           # Default configurations
│   └── data_loader.py      # Data management
└── utils/
    ├── metrics.py          # Metrics calculations
    └── config_manager.py   # Config state management
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

- Python 3.8+
- Streamlit 1.28+
- Pandas 2.0+
- NumPy 1.24+
- Plotly 5.0+

## 📄 Documentation

See `PROJECT_PLAN.md` for comprehensive documentation including:
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