# `services/utils`

This directory contains shared helper modules used across the modular Hurakan services.

## `.py` scripts

### `config.py`
- Centralizes logger creation and standard logging behavior for the service layer.

### `geo_math.py`
- Provides interpolation, Haversine distance, bearing, Saffir-category, and cluster-dispersion helpers.

### `init_folders.py`
- Reads `.env` path settings and creates the directory structure required by the application.

### `readers.py`
- Parses timestamps and basin names from filenames, reads TempestExtremes stitch files, and loads threshold CSV data.

### `viz_tools.py`
- Provides shared Matplotlib styling, plot saving, and category-color utilities.

### `__init__.py`
- Marks the directory as a Python package.
