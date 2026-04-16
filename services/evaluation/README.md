# `whole version/services/evaluation`

This directory contains historical evaluation tools for forecast trajectories.

## `.py` scripts

### `evaluation.py`
- Loads historical best-track reference data from CSV.
- Assigns stitched trajectories to named storms based on temporal overlap.
- Computes ensemble RMSE curves against reference tracks and exports plots and CSV results.

### `__init__.py`
- Marks the directory as a Python package.
