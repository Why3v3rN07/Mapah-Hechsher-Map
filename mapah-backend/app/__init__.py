from flask import Flask
from flask_cors import CORS

from .config import Config
from .extensions import db, migrate, login_manager


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__)
    CORS(app)
    app.config.from_object(Config)

    # Allow tests (or other callers) to override config before extensions bind
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)

    # Flask-Login setup
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    login_manager.init_app(app)

    from .routes import main_bp
    app.register_blueprint(main_bp, url_prefix="/api")

    from .auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix="/auth")

    return app


# Flask-Login needs this to reload a user from the session
@login_manager.user_loader
def load_user(user_id: str):
    from .models import Users
    return Users.query.get(int(user_id))
