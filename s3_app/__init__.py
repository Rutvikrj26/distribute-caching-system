from flask import Flask
from config import Config


s3_app = Flask(__name__, static_url_path="", static_folder="static")
s3_app.config.from_object(Config)

from s3_app import routes
