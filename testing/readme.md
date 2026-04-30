# `testing`

This directory contains manual testing and utility entry points for the modular pipeline.

- [About](#about)
- [Usage](#usage)
- [Built Using](#built_using)
- [Scripts](#scripts)
- [TODO](#ToDo)

## About <a name = "about"></a>
Contains some utilities for manual or batch process

## Usage <a name = "usage"></a>
To be used in the as utilities at the system console.

### Configuration <a name = "conf"></a>
These parameters need ocnfiguration:
- STITCH_DIR. Is an environmental variable
- OUTPUT_DIR. Is an environmental variable
- DATA_RAW_DIR. Local variable in program
- DATA_AUX_DIR. Is an environmental variable
- NODES_DIR. Is an environmental variable

## Built using <a name = "built_using"></a>
- [Python](https://python.org/) - Python is a programming language that lets you work quickly and integrate systems more effectively.

## Scripts <a name = "scripts"></a>

### `generate_map_only.py`
- Manually triggers combined map generation for a specific forecast timestamp.

### `process_test.py`
- Batch-runs the processing pipeline over Atlantic and Pacific NetCDF folders.
- Skips already processed files and logs success or failure for each run.

### `__init__.py`
- Marks the directory as a Python package.

## ToDo <a name = "ToDo"></a>
- Incorporate user management (as in create_user.py)
- Add tests after the installation to ensure correct functionality
- Incorporation of real-time measurements (e.g., wind data from CYGNSS) to refine the representation of cyclonic intensity
