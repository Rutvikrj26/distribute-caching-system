from flask import Flask
from collections import OrderedDict
from config import Config


# Actual Memcache Info
global memcache
memcache = OrderedDict()

memapp = Flask(__name__, static_url_path="", static_folder="static")
memapp.config.from_object(Config)

from memapp import routes, models
