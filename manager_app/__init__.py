from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config


manager_app = Flask(__name__, static_url_path="", static_folder="static")
manager_app.config.from_object(Config)
db = SQLAlchemy(manager_app)
migrate = Migrate(manager_app, db)

from manager_app import routes
