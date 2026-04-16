# `whole version/services/clusterer`

This directory contains the trajectory clustering engine.

## `.py` scripts

### `cluster_engine.py`
- Clusters trajectories with hierarchical single-linkage clustering.
- Computes pairwise mean distances only over the temporal overlap between trajectories.
- Filters clusters by minimum size and can generate a 3D cluster visualization.

### `__init__.py`
- Marks the directory as a Python package.

## Other content
- `thresholds.csv` stores threshold values used by downstream clustering and decision logic.
