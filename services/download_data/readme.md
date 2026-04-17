# `whole version/services/download_data`

This directory contains the modular data-download service for WeatherNext forecasts and NOAA shapefiles.

## `.py` scripts

### `config.py`
- Centralizes download paths, Earth Engine assets, weather-variable mappings, and Google Drive configuration.

### `download_all_nc_nonstop.py`
- Long-running downloader that continuously exports WeatherNext forecast blocks from Earth Engine to Google Drive.
- Downloads those blocks locally, converts them to NetCDF, adds elevation, cleans temporary files, and refreshes NOAA shapefiles.

### `download_all_nc_watchdog.py`
- Single-run variant intended for scheduled or watchdog execution.
- Performs one end-to-end retrieval cycle for Pacific and Atlantic data and then exits.

### `download_shp_NOAA.py`
- Downloads the latest NOAA tropical-cyclone shapefiles and builds a Folium map from the extracted layers.

## Other content
- Log files and credential files in this folder support the download workflows rather than define application logic.
