from flask import Flask
from config import Config


autoscaler_app = Flask(__name__, static_url_path="", static_folder="static")
autoscaler_app.config.from_object(Config)

from autoscaler_app import routes

routes.start_monitoring()
