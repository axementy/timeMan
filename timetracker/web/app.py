from flask import Flask

def create_app():
    app = Flask(__name__)
    app.secret_key = 'dev_secret_key_pomodoro' # IMPORTANT: Change for production

    # Configure static folder for CSS, JS, images etc.
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
