import os
from flask import Flask
from routes import routes_bp
from extensions import db, migrate, login_manager
from dotenv import load_dotenv

load_dotenv()

# Ensure required directories exist for system operation

def create_app():
    """Application factory to initialize Flask and its extensions."""
    app = Flask(__name__)

    # --- Configuration Setup ---
    # Using absolute path for the SQLite database
    base_dir = os.path.abspath(os.path.dirname(__file__))
    
    # Ensure DATABASE_FILE from .env is converted to an absolute path dynamically based on base_dir (e.g. /app/...)
    db_file = os.getenv("DATABASE_FILE", "./data/db/app_database.db").lstrip("./")
    db_path = os.path.join(base_dir, db_file)
    
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # --- Initialize Extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    
    login_manager.init_app(app)
    login_manager.login_view = 'routes.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    # --- Register Blueprints ---
    app.register_blueprint(routes_bp)
    
    return app

app = create_app()

if __name__ == "__main__":
    # Create database tables within the app context if they don't exist
    with app.app_context():
        db.create_all()
        
    print("Starting Hurakan Flask Server...")
    # Running on 0.0.0.0 to allow access within Docker or local network
    app.run(debug=True, host='0.0.0.0', port=8081)