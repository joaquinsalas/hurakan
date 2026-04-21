# Hurakán File Structure and Data Pipeline

This document describes the organizational structure, data flow, and primary components of the **Hurakán** system, an interactive platform designed to detect and monitor potential tropical cyclones.

## Table of Contents
- [Project Structure](#project-structure)
- [Data Pipeline](#data-pipeline)
  - [1. Downloaded Data](#downloaded-data)
  - [2. Processed Data](#processed-data)
  - [3. Generated Maps](#generated-maps)
- [Databases and Environment Data](#databases-and-environment-data)
- [Services Overview](#services-overview)

---

## Project Structure <a name="project-structure"></a>

Hurakán relies on a modular, microservice-based architecture managed by Docker (`docker-compose.yml`). The primary directories include:

- **`core_app/`**: Contains the Flask frontend responsible for securely handling user authentication (`/login`, `/logout`), serving the web interface, and rendering interactive interactive maps.
- **`services/`**: The backend engine of Hurakán. Contains independent modules handling downloading, clustering, classification, processing, evaluation, and tracking of meteorological data.
- **`nginx/`**: Contains the reverse-proxy configuration to handle incoming traffic securely and route it to the internal Flask and API services.
- **`testing/`**: Contains scripts and utilities for performing manual system checks and validations.

---

## Data Pipeline <a name="data-pipeline"></a>

The system generates 15-day forecasts involving multiple probabilistic trajectories based on massive meteorological datasets.

### 1. Downloaded Data <a name="downloaded-data"></a>
Meteorological variables are historically forecasted using **GenCast** and **FGN** capabilities via Google Earth Engine and the WeatherNext Gen / WeatherNext 2 catalogs. These raw inputs act as the initial input for creating probabilistic trajectories.

### 2. Processed Data <a name="processed-data"></a>
The downloaded ensemble datasets undergo thorough processing. Given the geographical position of Mexico, the outputs are partitioned into two main region files:
- **Eastern Pacific Ocean** basin.
- **North Atlantic Ocean** basin.

### 3. Generated Maps <a name="generated-maps"></a>
After trajectory processing and ensemble clustering, the data goes through qualitative mappings. Each viable meteorological subset produces an interactive mapping layer displaying features like "Spaghetti" views (consensus across trajectory models) and Saffir-Simpson velocity scales mapped onto uncertainty cones.

---

## Databases and Environment Data <a name="databases-and-environment-data"></a>

- **Databases**: A dedicated volume/container handles user credentials securely, guaranteeing access restriction to the Hurakán dashboard. 
- **Environment variables**: System secrets, Google Earth API keys, and internal endpoint configurations are supplied via a `.env` file (template provided as `.env.example`).
- **Heavy Volume Exclusions**: Massive processed model files are ignored by version control mechanisms (`.gitignore`) and handled securely via specialized data drives or cloud object storage.

---

## Services Overview <a name="services-overview"></a>
The `services/` folder holds targeted processing tools:
- `download_data/`: Fetches initial meteorological sets.
- `processor/`: Operations pipeline handling the NetCDF files.
- `clusterer/`: Engine calculating and evaluating trajectory consensus.
- `classifier/`: Service interpreting if a tracked storm has formed a mature tropical cyclone. 
- `evaluation/` & `tracking/`: Retrospective diagnostics and tracking logic.
- `utils/`: Shared utilities.
