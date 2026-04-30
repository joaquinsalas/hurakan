# `core_app`

This directory contains the Flask web application for the modular Hurakan deployment.

- [About](#about)
- [Usage](#usage)
- [Built Using](#built_using)
- [Scripts](#scripts)
- [TODO](#ToDo)

## About <a name = "about"></a>
This is one of the services published in the Docker container, that manages the multi-service web nterfase using Flask. By definition opens in port 8081.

## Usage <a name = "usage"></a>
As a multi-service web platform, the endpoints used are:
- 0.0.0.0:port/login
- 0.0.0.0:port/logout
- 0.0.0.0:port/upload_map
- 0.0.0.0:port/health

### Configuration <a name = "conf"></a>
These parameters need ocnfiguration:
- Database file. Is an environmental variable
- Secret Key. Is an environmental variable
- SQLALCHEMY_DATABASE_URI. Is an evironmental variable
- SQLALCHEMY_TRACK_MODIFICATIONS. Is an environmental variable
- Hurakán users. Need to use create_user.py to add/delete users to the system

## Built using <a name = "built_using"></a>
- [Flask](https://flask.palletsprojects.com/) - Lightweight WSGI web application framework
- [SQLite](https://sqlite.org/) - SQLite is a C-language library that implements a small, fast, self-contained, high-reliability, full-featured, SQL database engine.
- [Docker](https://docker.com/) - A safer container ecosystem
- [OpenStreetMap](https://www.openstreetmap.org/) - Map of the world
- [Leaflet](https://leafletjs.com/) - An open-source JavaScript library
for mobile-friendly interactive maps
- [CARTO](https://catro.com/) - The Agentic GIS Platform

## Scripts <a name = "scripts"></a>

### `app.py`
- Creates the Flask application with an application-factory pattern.
- Loads environment variables, configures the SQLite database path, and initializes Flask extensions.
- Registers the main routes blueprint and starts the server when run directly.

### `extensions.py`
- Defines shared Flask extensions:
  - `SQLAlchemy`
  - `Migrate`
  - `LoginManager`

### `forms.py`
- Defines the login form used by the frontend.

### `models.py`
- Defines the authenticated `User` model and password helpers.
- Registers the `user_loader` used by Flask-Login.

### `routes.py`
- Handles login/logout and serves the latest processed HTML map.
- Provides a `/upload_map` endpoint so backend services can publish newly generated maps.
- Exposes a `/health` endpoint and a maintenance-mode path through the main route.

## ToDo <a name = "ToDo"></a>
- Incorporate user management (as in create_user.py)
- Add tests after the installation to ensure correct functionality
- Incorporation of real-time measurements (e.g., wind data from CYGNSS) to refine the representation of cyclonic intensity

