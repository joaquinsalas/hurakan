# `services`

This directory is the backend service layer for the modular Hurakan system.

- [About](#about)
- [Usage](#usage)
- [Built Using](#built_using)
- [Scripts](#scripts)
- [TODO](#ToDo)

## About <a name = "about"></a>
These are two of the services published in the Docker container:
- classifier: Allows the classification of the trajectories as potential tropical cyclones and the evaluation of the quality of the prediction for tropical cyclones and the atmospheric data processed as mean trajectory and uncertainty cone. By definition opens at port 8000
- processor: Uses TempestExtremes to identify trajectories and then calculates the cluster of trajectories 

## Usage <a name = "usage"></a>
As a multi-service web platform, the endpoints used are:
- classifier:port/predict
- processor is a background service to transform atmospheric data files into trajectories, clustering such trajectories and construct the map for visualization

### Configuration <a name = "conf"></a>
These parameters need configuration:
- CLASSIFIER_API_URL. Is an environmental variable
- DATA_RAW_DIR. Is an environmental variable
- TEMP_DIR. Is an evironmental variable
- NODES_DIR. Is an environmental variable
- STITCH_DIR. Is an environmental variable
- OUTPUT_DIR. Is an environmental variable
- HURAKAN_PROB_THR. Is an environmental variable
- THRESHOLDS_CSV. Is an environmental variable


## Built using <a name = "built_using"></a>
- [FastAPI service](https://fastapi.tiangolo.com/) - FastAPI framework, high performance, easy to learn, fast to code, ready for production
- [PyTorch](https://pytorch.org/) - PyTorch is an open-source deep learning library
- [Docker](https://docker.com/) - A safer container ecosystem
- [NetCDF](https://en.wikipedia.org/wiki/NetCDF) - Scientific Data Formats by Unidata program at  University Corporation for Atmospheric Research (UCAR)

## Scripts <a name = "scripts"></a>

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

## ToDo <a name = "ToDo"></a>
- Add tests after the installation to ensure correct functionality
- Incorporation of real-time measurements (e.g., wind data from CYGNSS) to refine the representation of cyclonic intensity
