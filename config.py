import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    FRONTEND_URL = "http://127.0.0.1:5000/"
    MEMAPP_URL = "http://127.0.0.1:5001/"
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://ece1779:ece1779@localhost/ece'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

    AWS_REGION = 'us-east-2'
    S3_BUCKET_NAME = "ece-a3-gb"
    # Cloudwatch metrics - use these, so we don't accidentally make doubles that cost $$$
    cloudwatch_namespace = 'ECE1779/Grp25'
    misses = 'misses'
    hits = 'hits'
    num_items_in_cache = 'number_of_items_in_cache'
    size_items_in_Megabytes = 'cache_size'
    num_active_nodes = 'num_active_nodes'
    num_posts_served = 'posts_served'
