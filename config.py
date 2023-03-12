import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
      'mysql+pymysql://admin:i_am_from_beyond@ece.cgdahn06kt1q.us-east-2.rds.amazonaws.com:3306/ece'
        # 'sqlite:///' + os.path.join(basedir, 'app.db')
#        'mysql+pymysql://ece1779:ece1779@localhost/ece'

    # Going to RDS is as simple as changing the Database URI
    # mysql://admin:i_am_from_beyond@ece.cgdahn06kt1q.us-east-2.rds.amazonaws.com:3306/ece

    AWS_REGION='us-east-1'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Shouldn't need this folder anymore
    # UPLOAD_FOLDER = 'static'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    S3_BUCKET_NAME = "ece1779-group25"
    MAX_NODES = 8

    # IP ADDRESSES
    FRONTEND_URL = "http://3.139.103.194:5000/"
    MANAGER_APP_URL = "http://3.139.103.194:5001/"
    AUTOSCALER_APP_URL = "http://3.139.103.194:5002/"
    S3_APP_URL = "http://3.139.103.194:5003//"
    MEMAPP_0_URL = "http://3.145.153.213:5000/"
    MEMAPP_1_URL = "http://3.145.7.90:5000/"
    MEMAPP_2_URL = "http://3.142.135.104:5000/"
    MEMAPP_3_URL = "http://3.12.107.84:5000/"
    MEMAPP_4_URL = "http://18.118.207.236:5000/"
    MEMAPP_5_URL = "http://3.15.223.27:5000/"
    MEMAPP_6_URL = "http://18.188.246.106:5000/"
    MEMAPP_7_URL = "http://18.224.69.57:5000/"

    # Cloudwatch metrics - use these, so we don't accidentally make doubles that cost $$$
    misses = "misses"
    hits = "hits"
    num_items_in_cache = "num_items_in_cache"
    size_items_in_Megabytes = "size_items_in_Megabytes"
    num_active_nodes = "num_active_nodes"
    num_posts_served = "num_posts_served"
