import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://ece1779:ece1779@localhost/ece'

    # Going to RDS is as simple as changing the Database URI
    # mysql://admin:i_am_from_beyond@ece.cgdahn06kt1q.us-east-2.rds.amazonaws.com:3306/ece

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Shouldn't need this folder anymore
    # UPLOAD_FOLDER = 'static'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    S3_BUCKET_NAME = "ece1779-group25"
    MAX_NODES = 8

    # IP ADDRESSES
    FRONTEND_URL = "http://127.0.0.1:5000/"
    MANAGER_APP_URL = "http://127.0.0.1:5001/"
    AUTOSCALER_APP_URL = "http://127.0.0.1:5002/"
    S3_APP_URL = "http://127.0.0.1:5003/"
    MEMAPP_0_URL = "http://127.0.0.1:5004/"
    MEMAPP_1_URL = "http://127.0.0.1:5005/"
    MEMAPP_2_URL = "http://127.0.0.1:5006/"
    MEMAPP_3_URL = "http://127.0.0.1:5007/"
    MEMAPP_4_URL = "http://127.0.0.1:5008/"
    MEMAPP_5_URL = "http://127.0.0.1:5009/"
    MEMAPP_6_URL = "http://127.0.0.1:5010/"
    MEMAPP_7_URL = "http://127.0.0.1:5011/"

    # Cloudwatch metrics - use these, so we don't accidentally make doubles that cost $$$
    misses = "misses"
    hits = "hits"
    num_items_in_cache = "num_items_in_cache"
    size_items_in_Megabytes = "size_items_in_Megabytes"
    num_active_nodes = "num_active_nodes"
    num_posts_served = "num_posts_served"
