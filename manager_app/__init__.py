from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from flask_bootstrap import Bootstrap


manager_app = Flask(__name__, static_url_path="", static_folder="static")
manager_app.config.from_object(Config)
db = SQLAlchemy(manager_app)
migrate = Migrate(manager_app, db)
bootstrap = Bootstrap(manager_app)

from manager_app import routes, models

with manager_app.app_context():
    db.create_all()
    default_config = models.ManagerConfig()
    db.session.add(default_config)
    db.session.commit()