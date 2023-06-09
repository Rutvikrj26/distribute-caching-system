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
    # creating the tables in the database
    db.create_all()
    # Creating the default config
    default_config = models.ManagerConfig()
    initial_memcache_config = models.MemcacheConfig()
    # adding the default config
    db.session.add(default_config)
    db.session.add(initial_memcache_config)
    # commiting the changes
    db.session.commit()