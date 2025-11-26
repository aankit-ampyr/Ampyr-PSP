# Changelog

All notable changes to the BESS Sizing Tool project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.1] - 2025-11-24

### Fixed
- **Streamlit Cloud Deployment Error** - Python 3.13 compatibility issues
  - **Root Cause:** Old package versions incompatible with Python 3.13
  - `numpy==1.24.0` failed to build (requires `distutils`, removed in Python 3.12+)
  - Streamlit Cloud upgraded to Python 3.13.9 by default
  - Caused "installer returned a non-zero exit code" deployment failure
  - **Initial Fix:** Removed editable install (`-e .`) from requirements.txt
    - Editable installs not supported on Streamlit Cloud
    - Streamlit Cloud automatically adds repository root to PYTHONPATH
  - **Complete Fix:** Updated all packages to Python 3.13-compatible versions

### Changed
- **Python Version** ([runtime.txt](runtime.txt))
  - Updated from `python-3.11` to `python-3.13`
  - Matches Streamlit Cloud default environment

- **Package Versions** ([requirements.txt](requirements.txt))
  - **streamlit:** 1.28.0 → 1.39.0 (latest stable, Nov 2024)
  - **pandas:** 2.0.0 → 2.2.3 (latest stable 2.x, Sep 2024)
  - **numpy:** 1.24.0 → 2.1.3 (Python 3.13 compatible, Oct 2024)
  - **plotly:** 5.0.0 → 5.24.1 (latest stable, Oct 2024)
  - All packages now fully compatible with Python 3.13

- **setup.py**
  - Updated version to 1.1.1
  - Updated `python_requires` from `>=3.8` to `>=3.11`
  - Updated `install_requires` to match new package versions
  - All dependencies use `>=` for forward compatibility

- **requirements.txt** - Updated comment to accurately reflect Streamlit Cloud behavior
  - Corrected misleading note about `-e .` working on Streamlit Cloud
  - Added clear explanation of automatic PYTHONPATH configuration

### Documentation
- **bug_report_analysis.md** - Corrected Bug #14 deployment note (line 999-1002)
  - Previous note incorrectly claimed `-e .` works on Streamlit Cloud
  - Updated with accurate information about cloud vs local deployment

### Upgrade Notes
- **Breaking Change:** Minimum Python version now 3.11 (was 3.8)
- **NumPy Major Version:** Upgraded from 1.x to 2.x
  - NumPy 2.x is backward compatible for most use cases
  - If issues occur, may need minor code adjustments
- **Recommended:** Test locally with Python 3.13 before deploying

---

## [1.1.0] - 2025-11-23

### Added
- **Logging Framework** ([utils/logger.py](utils/logger.py))
  - Centralized logging configuration for consistent application-wide logging
  - Formatted log messages with timestamps and module identification
  - Configurable log levels (INFO, WARNING, ERROR)
  - Professional error handling and debugging capabilities

- **Package-level Imports**
  - Enhanced `src/__init__.py` with public API exports
  - Enhanced `utils/__init__.py` with utility function exports
  - Added package docstrings and version information
  - Enables convenient imports: `from src import BatterySystem`

### Changed
- **Dependency Version Pinning** ([requirements.txt](requirements.txt))
  - Pinned all dependencies to exact versions for reproducible builds
  - `streamlit==1.28.0` (was `>=1.28.0`)
  - `pandas==2.0.0` (was `>=2.0.0`)
  - `numpy==1.24.0` (was `>=1.24.0`)
  - `plotly==5.0.0` (was `>=5.0.0`)
  - Prevents breaking changes from automatic dependency updates

- **Improved Error Handling** ([src/data_loader.py](src/data_loader.py))
  - Replaced `print()` statements with proper logging
  - Added structured error messages with logger.error() and logger.warning()
  - Maintained Streamlit UI error messages for user visibility
  - Better debugging with timestamped log entries

### Fixed
- **Bug #16**: Implemented professional logging framework (replaced console print statements)
- **Bug #17**: Removed unused numpy import from [pages/2_calculation_logic.py](pages/2_calculation_logic.py)
- **Bug #19**: Pinned dependency versions to prevent breaking changes
- **Bug #20**: Confirmed desktop.ini properly excluded from git (already in .gitignore)
- **Bug #21**: Enhanced __init__.py files with package-level imports and documentation

### Technical Improvements
- Code cleanliness: Removed unused imports
- Professional packaging: Enhanced package structure with proper __init__.py files
- Production readiness: Added comprehensive logging infrastructure
- Dependency management: Exact version pinning for stability
- Better debugging: Structured logging with timestamps and module identification

### Documentation
- All bug fixes documented in [BUG_REPORT_ANALYSIS.md](BUG_REPORT_ANALYSIS.md)
- Updated executive summary: 16 bugs fixed/resolved
- Comprehensive implementation details for each fix

---

## [1.0.0] - 2024-11-22

### Added
- Initial release of BESS Sizing Tool
- Core battery simulation engine
- Solar profile data loading
- Four-page Streamlit application:
  - Configuration management
  - Battery simulation
  - Calculation logic documentation
  - Advanced optimization analysis
- Two optimization algorithms:
  - High-Yield Knee Algorithm
  - Marginal Improvement Threshold
- Comprehensive metrics and visualizations
- CSV export functionality

### Core Features
- Binary delivery constraint (25 MW target)
- Solar-only charging (no grid)
- SOC limits (5-95%)
- Maximum 2 cycles per day
- Degradation tracking (0.15% per cycle)
- Round-trip efficiency (87%)
- Interactive Plotly charts

### Fixed (Initial Bug Fixes - v1.0.0)
- **Bug #1**: Power/Energy unit confusion in deliverability check (CRITICAL)
- **Bug #2**: Charge rate units conversion error (CRITICAL)
- **Bug #4**: Incorrect marginal gains calculation (HIGH)
- **Bug #5**: Marginal gains denominator error (HIGH)
- **Bug #6**: Total delivery hours calculation error (HIGH)
- **Bug #7**: Enhanced metrics display with additional fields
- **Bug #8**: Removed synthetic solar profile fallback (MEDIUM)
- **Bug #10**: Fixed solar profile path security (MEDIUM)
- **Bug #11**: Missing imports in optimization page (MEDIUM)
- **Bug #12**: Added package initialization with setup.py (MEDIUM)
- **Bug #14**: Removed unnecessary sys.path manipulation (LOW)

### Deferred
- **Bug #3**: Degradation display calculation (to be revisited)

---

## Version History Summary

- **v1.1.0** (2025-11-23): Production hardening - logging, pinned dependencies, code cleanup
- **v1.0.0** (2024-11-22): Initial release with core features and critical bug fixes

---

## Upgrade Guide

### From v1.0.0 to v1.1.0

**Requirements Update:**
```bash
# Reinstall dependencies with exact versions
pip install -r requirements.txt
```

**Code Changes:**
- No breaking changes
- Existing code continues to work
- Optional: Use new package-level imports for convenience
  - Before: `from src.battery_simulator import BatterySystem`
  - After: `from src import BatterySystem` (both work)

**New Features:**
- Logging is automatically enabled in src/data_loader.py
- Check console/logs for structured error messages with timestamps
- No configuration required

---

## Bug Tracking

For detailed bug analysis and fixes, see [BUG_REPORT_ANALYSIS.md](BUG_REPORT_ANALYSIS.md)

**Status Summary:**
- ✅ 16 Bugs Fixed/Resolved
- ⏸️ 1 Bug Deferred (Bug #3)
- ⚙️ 5+ Bugs Confirmed (remaining for future work)

---

## Contributing

When contributing, please:
1. Update this CHANGELOG.md with your changes
2. Follow [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format
3. Use semantic versioning for releases
4. Document bug fixes in BUG_REPORT_ANALYSIS.md

---

**Last Updated:** 2025-11-23
