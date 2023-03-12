from flask import Flask
from collections import OrderedDict
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config


# Actual Memcache Info
global memcache
memcache = OrderedDict()

memapp = Flask(__name__, static_url_path="", static_folder="static")
memapp.config.from_object(Config)
# db = SQLAlchemy(memapp)
# migrate = Migrate(memapp, db)

from memapp import routes

# with memapp.app_context():
#     db.create_all()