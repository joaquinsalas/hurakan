# `whole version/services/processor`

This directory contains the core operational pipeline that processes ensemble NetCDF files and turns them into interactive maps.

## `.py` scripts

### `analysis.py`
- Computes derived products from trajectory sets, including initial dispersion, smoothed probable tracks, uncertainty cones, and outlier filtering.

### `monitor_service.py`
- Watches the raw NetCDF directory with `watchdog`.
- Triggers processing when a new basin file appears and generates a combined map once both Pacific and Atlantic files for a cycle are ready.

### `processing.py`
- Splits ensemble NetCDF files into member-specific temporary files.
- Runs TempestExtremes `DetectNodes` and `StitchNodes` in parallel.
- Records processing performance metrics and collects stitched trajectories by region.

### `visualization.py`
- Generates the final combined Folium HTML map.
- Merges basin trajectories, applies clustering, calls the classifier service, and adds probable tracks, cones, legends, metadata, and timeline controls.

### `__init__.py`
- Marks the directory as a Python package.
