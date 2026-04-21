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
Python and other software is needed. For simplicity, we recommend to use a Docker container; then this app can be running in Windows, macOs o GNU/Linux, whatever OS you have.
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
python3 -m venv .venv
```````````````````````````````````````````````````````````````````````````````````
> [!NOTE]
> Note: python3 is the command to execute Python 3.11+ in the original system
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
4. Make a copy of the environmental variables required
-Windows:
```````````````````````````````````````````````````````````````````````````````````
(.venv) hurakan$ copy .env.example .env
```````````````````````````````````````````````````````````````````````````````````
-macOS / GNU/Linux:
```````````````````````````````````````````````````````````````````````````````````
(.venv) hurakan$ cp .env.example .env
```````````````````````````````````````````````````````````````````````````````````
> [!NOTE]
> Note: You can export the variables in the .env file or install python-dotenv for the next step
Install python-dotenv
```````````````````````````````````````````````````````````````````````````````````
(.venv) hurakan$ pip install python-dotenv
```````````````````````````````````````````````````````````````````````````````````
5. Create the file structure required
```````````````````````````````````````````````````````````````````````````````````
(.venv) hurakan$ python services/utils/init_folders.py
```````````````````````````````````````````````````````````````````````````````````
> [!NOTE]
> Note: python is the command to executo Python 3.11+ inside the virtual environment .venv
6. Build and run docker image with services
```````````````````````````````````````````````````````
(.venv) hurakan$ docker compose up --build
```````````````````````````````````````````````````````
> [!TIP]
> Note: Can take a lot of time for the first time, depending on the download speed for the internet service
Getting output like
```````````````````````````````````````````````````````
...
Attaching to classifier-1, core_app-1, processor-1, redis-1
core_app-1  | Database: /app/data/db/app_database.db
core_app-1  | Starting Hurakan Flask Server...
core_app-1  |  * Serving Flask app 'app'
core_app-1  |  * Debug mode: on
core_app-1  | 2026-04-21 03:23:03,084 - werkzeug - INFO - WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
core_app-1  |  * Running on all addresses (0.0.0.0)
core_app-1  |  * Running on http://127.0.0.1:8081
core_app-1  |  * Running on http://172.18.0.5:8081
core_app-1  | 2026-04-21 03:23:03,085 - werkzeug - INFO - Press CTRL+C to quit
core_app-1  | 2026-04-21 03:23:03,086 - werkzeug - INFO -  * Restarting with stat
core_app-1  | 2026-04-21 03:23:03,831 - werkzeug - WARNING -  * Debugger is active!
core_app-1  | 2026-04-21 03:23:03,832 - werkzeug - INFO -  * Debugger PIN: 847-688-636
processor-1  | 2026-04-21 03:23:04,244 - monitorService - INFO - --------------------------------------------------
processor-1  | 2026-04-21 03:23:04,244 - monitorService - INFO - Hurakan Monitor Service is now ACTIVE
processor-1  | 2026-04-21 03:23:04,245 - monitorService - INFO - Monitoring: ./data/raw_nc
processor-1  | 2026-04-21 03:23:04,245 - monitorService - INFO - Waiting for dual-basin NetCDF files...
processor-1  | 2026-04-21 03:23:04,245 - monitorService - INFO - --------------------------------------------------
classifier-1  | INFO:     Started server process [1]
classifier-1  | INFO:     Waiting for application startup.
classifier-1  | INFO:     Application startup complete.
classifier-1  | INFO:     Uvicorn running on http://0.0.0.0:8082 (Press CTRL+C to quit)
...
```````````````````````````````````````````````````````
7. Install the requirements for core_app
```````````````````````````````````````````````````````````````````````````````````
(.venv) hurakan$ cd core_app
(.venv) hurakan/core_app$ pip install -r requirements.txt
```````````````````````````````````````````````````````````````````````````````````
8. Create authorized users to access Hurakán
```````````````````````````````````````````````````````````````````````````````````
(.venv) hurakan/core_app$ python create_users.py
```````````````````````````````````````````````````````````````````````````````````
9. Install the requirements to download data
```````````````````````````````````````````````````````````````````````````````````
(.venv) hurakan/core_app$ cd ..
(.venv) hurakan$ pip install -r librerias_download.txt
```````````````````````````````````````````````````````````````````````````````````
10. Generar credenciales en Google Drive API
> [!NOTE]
> Note: Get both the Token (JSON type) and Credentials (JSON type) files to get access to Google Drive API 
11. Modify the values of some directories in your device in the file .env with an editor
```````````````````````````````````````````````````````````````````````````````````
(.venv) hurakan$ nano .env
```````````````````````````````````````````````````````````````````````````````````
> [!NOTE]
> Note: Change TOKEN_FILE and CREDENTIALS_FILE variables for get access to Google Drive API and DATA_RAW_DIR whre the atmospheric data will be downloaded
12. Execute data downloader:
As a shell script:
```````````````````````````````````````````````````````````````````````````````````
(.venv) hurakan$ cd services/download_data
(.venv) hurakan/services/download_data$ run_download.sh
```````````````````````````````````````````````````````````````````````````````````
or create a file service with this downloader (macOS/ GNU/Linux):
```````````````````````````````````````````````````````````````````````````````````
sudo nano /etc/systemd/system/download_weather.service
```````````````````````````````````````````````````````````````````````````````````
with the file download_water.service as:
```````````````````````````````````````````````````````````````````````````````````
[Unit]
Description=Continuous download of WeatherNext NetCDF
After=network-online.target
Wnats=network-online.target

[Service]
Type=simple
User=<your_user>
ExecStart=/bin/bash -lc cd "/opt/hurakan/services/download_data" && "rn_download.sh"
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```````````````````````````````````````````````````````````````````````````````````
Life-cycle of the downloader service:
```````````````````````````````````````````````````````````````````````````````````
sudo systemctl enable download_weather.service
sudo systemctl start download_weather.service
sudo systemctl stop download_weather.service
sudo systemctl disable download_weather.service
```````````````````````````````````````````````````````````````````````````````````


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
