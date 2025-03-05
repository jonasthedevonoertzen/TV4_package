# app.py

from flask import Flask
from flask_login import LoginManager
from story_creator import init_db  # Import the database initialization function
from story_creator.database_handler import get_user_by_email  # Import from the new database handler
import datetime  # Import datetime module

# Import blueprints
from blueprints.auth import auth_bp
from blueprints.main import main_bp

import time

def create_app():
    app = Flask(__name__)
    app.secret_key = 'different_secret_key'  # Replace with a secure key or load from environment variables

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_email):
        time.sleep(1)
        return get_user_by_email(user_email)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    # Context processor to inject 'current_year' into templates
    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.datetime.utcnow().year}

    # Initialize the database (moved to story_creator package)
    init_db()

    return app


app = create_app()


if __name__ == '__main__':
    app.run(debug=True)  # , host="0.0.0.0"
