# Hurakán
<p align="center"> This repository contains a version of a tropical-cyclone forecasting and analysis workflow.
    <br> 
</p>

## Table of Contents
- [About](#about)
- [Getting Started](#getting_started)
- [Usage](#usage)
- [Built Using](#built_using)
- [TODO](#ToDo)
- [Authors](#authors)
- [Acknowledgments](#acknowledgement)

## About <a name = "about"></a>
Hurakán is multi-service web-based platform that provides forecasts of tropical cyclone (TC) trajectories.

It integrates atmospheric scenarios produced by probabilistic data-driven forecasting systems. Also, it Uses globally available data, but requires Regions of Interest (RoI) to focus to certain areas like specific coastlines.


## Getting Started <a name = "getting_started"></a>
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. 
Python and other software is needed. For simplicity, we recommend to use a Docker container; then this app cna be running in Windows, macOs o GNU/Linux, whatever OS you have.
You need a computer as web server (where this project executes) and other as client (to interact with the web interfase) using a web browser (without Docker).

### Prerequisites
Hurakán rely on several Python (3.11+) libraries and Docker. When installing, the required libraries will be downloaded from open software repositories.
Docker Engine is open software, but Docker Desktop is propietary and required at least a subscription. For instructions to install on Windows. macOS o GNU/Linux see [Docker Desktop](https://docs.docker.com/desktop/#next-steps)
Hurakán also requires atmospherical data from a specific day, like for example, today.

### Installation Quick Look
1. Clone repository
``````````````````````````````````````````````````````````````````````````````````
git clone https://github.com/joaquinsalas/hurakan
cd hurakan
```````````````````````````````````````````````````````````````````````````````````
2. Build and run docker image with services
```````````````````````````````````````````````````````
docker compose up --build
```````````````````````````````````````````````````````

## Installation manual
For detailed instructions see [Installation](./core_app/docs/manuals/install.md) 

## Usage <a name = "usage"></a>
See [User manual](./core_app/docs/manuals/usermanual.md) for detailed instructions to use Hurakán.

### App files stucture
See [File Structure](./core_app/docs/manuals/filestructure.md) for visualizing the file organization for Hurakán.

## Built Using <a name = "built_using"></a>
- [Flask](https://flask.palletsprojects.com/) - Lightweight WSGI web application framework
- [Docker](https://docker.com/) - A safer container ecosystem
- [TempestExtremes](https://climate.ucdavis.edu/tempestextremes.php) - Collection of detection and characterization algorithms for large climate datasets
- [NodeJs](https://nodejs.org/en/) - Server Environment
- [OpenStreetMap](https://www.openstreetmap.org/) - Map of the world
- [Leaflet](https://leafletjs.com/) - An open-source JavaScript library
for mobile-friendly interactive maps
- [CARTO](https://catro.com/) - The Agentic GIS Platform

## ToDo <a name = "ToDo"></a>
- Add tests after the installation to ensure correct functionality
- Incorporation of real-time measurements (e.g., wind data from CYGNSS) to refine the representation of cyclonic intensity

## Authors <a name = "authors"></a>
- [@NathalieAlvarez](https://github.com/NathalieAlvarez) - data download, clustering, classifiers
- [@robertorojas11](https://github.com/robertorojas11) - trajectories, performance, systems engineering
- [@LuisManuelOrtiz](https://github.com/LuisManuelOrtiz) -
- [@YaelHuerta1](https://github.com/YaelHuerta1) - clustering, interfase, systems engineering
- [@joaquinsalas](https://github.com/joaquinsalas) - idea, algorithms, QA

See also the list of [contributors](https://github.com/joaquinsalas/graphs/contributors) who participated in this project.

## Acknowledgements <a name = "acknowledgement"></a>
We downloaded GenCast and FGN historical forecasts of meteorological variables from the Google Earth Engine WeatherNext Gen Forecasts and WeatherNext 2 data catalogs

