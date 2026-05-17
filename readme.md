# Hurakán
<p align="center"> This repository contains a version of a tropical-cyclone forecasting and analysis workflow.
    <br> 
</p>

## Table of Contents
- [About](#about)
- [Licensing](#licensing)
- [Getting Started](#getting_started)
- [Usage](#usage)
- [Built Using](#built_using)
- [TODO](#ToDo)
- [Authors](#authors)
- [Acknowledgments](#acknowledgement)

## About <a name = "about"></a>
Hurakán is multi-service web-based platform that provides forecasts of tropical cyclone (TC) trajectories.

It integrates atmospheric scenarios produced by probabilistic data-driven forecasting systems. The present implementation focuses on Regions of Interest (RoI) focused around the coastlines of Mexico.


## Licensing  <a name = "licensing"></a>

This code is distributed under the following licensing agreement

MIT License

Copyright (c) 2025 Instituto Politécnico Nacional

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.


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
- [FastAPI](https://fastapi.tiangolo.com) - FastAPI framework, high performance, easy to learn, fast to code, ready for production
- [PyTorch](https://pytorch.org) - PyTorch is an open-source deep learning library
- [NetCDF](https://en.wikipedia.org/wiki/NetCDF) - Scientific Data Formats by Unidata program at University Corporation for Atmospheric Research (UCAR)
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
- [@YaelHuerta1](https://github.com/YaelHuerta1) - clustering, interface, systems engineering
- [@joaquinsalas](https://github.com/joaquinsalas) - initial code for downloading, clustering, performance evaluation, funding grantee, coordination


See also the list of [contributors](https://github.com/joaquinsalas/hurakan/blob/main/acknowledgments/acknowledgments.md) who participated in this project.

## Acknowledgements <a name = "acknowledgement"></a>
We downloaded GenCast and FGN historical forecasts of meteorological variables from the Google Earth Engine WeatherNext Gen Forecasts and WeatherNext 2 data catalogs.
This work was partially supported  by SECIHTI via grant MADTEC-M-9 to Joaquín Salas, Roberto Rojas, and Yael Huerta. Nathalie Alvarez has been supported by a scholarship from SECIHTI.

