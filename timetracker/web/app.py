"""
This module contains the Flask application factory for the TimeTracker web interface.
"""
from flask import Flask

def create_app() -> Flask:
    """
    Creates and configures an instance of the Flask application.

    This function sets up the application's secret key for session management,
    configures paths for static files and templates (though defaults are often used),
    and registers the application's routes defined in `routes.py`.

    Returns:
        Flask: The configured Flask application instance.
    """
    app = Flask(__name__)

    # IMPORTANT: The secret key is crucial for session security.
    # This default key is for development only and MUST be changed for production environments.
    # Consider loading from an environment variable or a configuration file for production.
    app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev_secret_key_pomodoro_REPLACE_ME')

    # Static and template folder configuration (Flask defaults are usually sufficient)
    # Flask by default looks for a 'static' folder in the same directory as the app module,
    # or one specified by static_folder.
    # If app.py is in timetracker/web/, and static is timetracker/web/static/, it's default.
    # app.static_folder = 'static' (already default if 'static' is sibling to app.py's module)

    # Configure template folder
    # Flask by default looks for a 'templates' folder in the same directory as the app module.
    # If app.py is in timetracker/web/, and templates is timetracker/web/templates/, it's default.
    # app.template_folder = 'templates' (already default)

    # Import and register routes
    # Ensure routes.py is in the same directory or path is set up correctly.
    from . import routes 
    routes.init_app_routes(app)

    return app

if __name__ == '__main__':
    # This allows running the app directly using `python timetracker/web/app.py`
    # for development purposes.
    # For production, a WSGI server like Gunicorn or uWSGI would be used.
    app = create_app()
    # Note: The host '0.0.0.0' makes the app accessible from other devices on the network.
    # For security, '127.0.0.1' (default) restricts it to the local machine.
    # Debug mode should be False in production.
    app.run(host='0.0.0.0', port=5000, debug=True)
