# `whole version/services`

This directory is the backend service layer for the modular Hurakan system.

## `.py` scripts

### `__init__.py`
- Marks the directory as a Python package for cross-service imports.

## Subdirectory overview
- `classifier`: stacked ensemble inference service.
- `clusterer`: trajectory clustering logic.
- `download_data`: WeatherNext and NOAA ingestion pipeline.
- `downscaling`: precipitation and windspeed downscaling experiments.
- `evaluation`: forecast-versus-reference verification utilities.
- `processor`: TempestExtremes processing, analysis, monitoring, and map generation.
- `tracking`: package placeholder for tracking-related expansion.
- `utils`: shared helpers for logging, I/O, math, and plotting.
