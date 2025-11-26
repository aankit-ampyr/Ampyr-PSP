"""
Setup configuration for BESS Sizing Tool
Enables proper Python package management and eliminates sys.path manipulation
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="bess-sizing",
    version="1.2.0",
    description="Battery Energy Storage System (BESS) Sizing and Optimization Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="BESS Sizing Team",
    python_requires=">=3.9",

    # Package discovery
    packages=find_packages(include=["src", "src.*", "utils", "utils.*"]),

    # Dependencies
    install_requires=[
        "streamlit>=1.28.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "plotly>=5.0.0",
    ],

    # Development dependencies
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
        ],
    },

    # Package data
    package_data={
        "": ["*.csv", "*.md"],
    },
    include_package_data=True,

    # Entry points (optional - for CLI if needed in future)
    entry_points={
        "console_scripts": [
            # "bess-sizing=app:main",  # Uncomment if CLI entry point needed
        ],
    },

    # Classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
