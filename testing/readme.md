# `whole version/testing`

This directory contains manual testing and utility entry points for the modular pipeline.

## `.py` scripts

### `generate_map_only.py`
- Manually triggers combined map generation for a specific forecast timestamp.

### `process_test.py`
- Batch-runs the processing pipeline over Atlantic and Pacific NetCDF folders.
- Skips already processed files and logs success or failure for each run.

### `__init__.py`
- Marks the directory as a Python package.
