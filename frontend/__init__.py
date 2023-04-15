from flask import Flask
from config import Config
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import aws_helper

frontend = Flask(__name__)
frontend.config.from_object(Config)

bootstrap = Bootstrap(frontend)
db = SQLAlchemy(frontend)
bcrypt = Bcrypt(frontend)
login_manager = LoginManager(frontend)

login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

from frontend import routes, models

aws_helper.dynamo_delete_images_table()
aws_helper.dynamo_create_image_table()
