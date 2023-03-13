from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap


frontend = Flask(__name__)
frontend.config.from_object(Config)
db = SQLAlchemy(frontend)

migrate = Migrate(frontend, db)
bootstrap = Bootstrap(frontend)

from frontend import routes, models
