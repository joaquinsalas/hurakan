# `whole version/core_app`

This directory contains the Flask web application for the modular Hurakan deployment.

## `.py` scripts

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
