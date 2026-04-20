# `Hurakán Installation`

## Table of Contents
- [About](#about)
- [Getting Started](#getting_started)
- [Deployment](#deployment)
- [Usage](#usage)
- [Built Using](#built_using)
- [TODO](../TODO.md)
- [Authors](#authors)
- [Acknowledgments](#acknowledgement)

## About <a name = "about"></a>
Hurakán is multi-service web-based platform that provides forecasts of tropical cyclone (TC) trajectories.

It integrates atmospheric scenarios produced by probabilistic data-driven forecasting systems. Also, it Uses globally available data, but requires Regions of Interest (RoI) to focus to certain areas like specific coastlines.

Requires a web server (to donwload and process atmospheric data, and show them as interactive maps, on a daily basis; also, to classify the data aalyzed to improve the identification of possible tropical cyclones), and a web client. 


## Getting Started <a name = "getting_started"></a>
These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. 
Python and other software is needed. For simplicity, we recommend to use a Docker container; then this app cna be running in Windows, macOs o GNU/Linux, whatever OS you have.
You need a computer as web server (where this project executes) and other as client (to interact with the web interfase) using a web browser (without Docker).

### Prerequisites
Hurakán rely on several Python (3.11+) libraries and Docker. When installing, the required libraries will be downloaded from open software repositories.
Docker Engine is open software, but Docker Desktop is propietary and required at least a subscription. For instructions to install on Windows. macOS o GNU/Linux see [Docker Desktop](https://docs.docker.com/desktop/#next-steps)
Hurakán also requires atmospherical data from a specific day, like for example, today.

### Installation
1. Clone repository
``````````````````````````````````````````````````````````````````````````````````
git clone https://github.com/joaquinsalas/hurakan
cd hurakan
```````````````````````````````````````````````````````````````````````````````````
2.Create a virtual environment (required libraries installed only in the virtual environment)
```````````````````````````````````````````````````````````````````````````````````
python -m venv .venv
```````````````````````````````````````````````````````````````````````````````````
3.Activate the virtual environment
-Windows:
```````````````````````````````````````````````````````````````````````````````````
.venv\Scripts\activate
```````````````````````````````````````````````````````````````````````````````````
-macOS / GNU/Linux:
```````````````````````````````````````````````````````````````````````````````````
source .venv/bin/activate
```````````````````````````````````````````````````````````````````````````````````
After the activation, the system prompt includes the name and parenthesis: 
```````````````````````````````````````````````````````````````````````````````````
(.venv) hurakan$
```````````````````````````````````````````````````````````````````````````````````
4. Install dependencies
```````````````````````````````````````````````````````````````````````````````````
pip install -r librerias_download.txt
```````````````````````````````````````````````````````````````````````````````````
5. Build and run docker image with services
```````````````````````````````````````````````````````
docker compose up --build
```````````````````````````````````````````````````````
Getting output like
```````````````````````````````````````````````````````
 * Serving Flask app 'core_app/app.py'
 * Debug mode: off
2026-04-08 20:10:51,924 - werkzeug - INFO - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:5000
2026-04-08 20:10:51,925 - werkzeug - INFO - Press CTRL+C to quit
2026-04-08 20:11:06,794 - werkzeug - INFO - 127.0.0.1 - - [08/Apr/2026 20:11:06] "GET / HTTP/1.1" 302 -
2026-04-08 20:11:06,826 - werkzeug - INFO - 127.0.0.1 - - [08/Apr/2026 20:11:06] "GET /login?next=/ HTTP/1.1" 200 -
```````````````````````````````````````````````````````

## Usage <a name = "usage"></a>
To use the application, from a client machine
```````````````````````````````````````````````````````````````````````````````````
Open http://127.0.0.1:8081 to view in the browser.
```````````````````````````````````````````````````````````````````````````````````
For detailed information see [User Manual](./usermanual.md)

## Deployment <a name = "deployment"></a>
As mentioned, you can build the Docker image in Windows, macOS or GNU/Linux, but you must run the container in the same OS version (for example, build on Windows 11 and run on Windows 11).

To run the Docker container:
```````````````````````````````````````````````````````````````````````````````````
docker compose up
```````````````````````````````````````````````````````````````````````````````````

To stop the running services and remove the containers, networks and images defined in the file:
```````````````````````````````````````````````````````````````````````````````````
docker compose down
```````````````````````````````````````````````````````````````````````````````````

## Built Using <a name = "built_using"></a>
- [Flask](https://flask.palletsprojects.com/) - Lightweight WSGI web application framework
- [Docker](https://docker.com/) - A safer container ecosystem
- [TempestExtremes](https://climate.ucdavis.edu/tempestextremes.php) - Collection of detection and characterization algorithms for large climate datasets
- [OpenStreetMap](https://www.openstreetmap.org/) - Map of the world
- [Leaflet](https://leafletjs.com/) - An open-source JavaScript library
for mobile-friendly interactive maps
- [CARTO](https://catro.com/) - The Agentic GIS Platform

## ToDo <a name = "todo"></a>
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
