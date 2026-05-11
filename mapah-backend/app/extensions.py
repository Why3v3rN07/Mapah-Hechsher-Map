from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

# Extensions are created here and initialized in the app factory.

# SQLAlchemy instance (database connection and ORM)
db = SQLAlchemy()
# set up Flask-Migrate (database migrations)
migrate = Migrate()
# set up Flask-Login (user session management)
login_manager = LoginManager()
