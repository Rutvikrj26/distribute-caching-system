import aws_helper
from flask import Flask
from config import Config
from flask_bootstrap import Bootstrap


frontend = Flask(__name__)
frontend.config.from_object(Config)

bootstrap = Bootstrap(frontend)

from frontend import routes, models

aws_helper.dynamo_delete_images_table()
aws_helper.dynamo_create_image_table()
