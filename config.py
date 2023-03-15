import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
      'mysql+pymysql://admin:i_am_from_beyond@ece.cgdahn06kt1q.us-east-2.rds.amazonaws.com:3306/ece'
    # SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    #                           'mysql+pymysql://root:Gb2-mysql@localhost:3306/ece'
    # 'sqlite:///' + os.path.join(basedir, 'app.db')
#        'mysql+pymysql://ece1779:ece1779@localhost/ece'

    # Going to RDS is as simple as changing the Database URI
    # mysql://admin:i_am_from_beyond@ece.cgdahn06kt1q.us-east-2.rds.amazonaws.com:3306/ece

    AWS_REGION='us-east-2'

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Shouldn't need this folder anymore
    # UPLOAD_FOLDER = 'static'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    S3_BUCKET_NAME = "ece-a2"
    MAX_NODES = 8

    # IP ADDRESSES
    FRONTEND_URL = "http://3.135.219.79:5000/"
    MANAGER_APP_URL = "http://3.135.219.79:5001/"
    AUTOSCALER_APP_URL = "http://3.135.219.79:5002/"
    S3_APP_URL = "http://3.135.219.79:5003/"
    MEMAPP_0_URL = "http://3.22.81.223:5000/"
    MEMAPP_1_URL = "http://18.189.141.115:5000/"
    MEMAPP_2_URL = "http://3.144.108.20:5000/"
    MEMAPP_3_URL = "http://3.144.3.115:5000/"
    MEMAPP_4_URL = "http://18.222.112.185:5000/"
    MEMAPP_5_URL = "http://3.145.85.161:5000/"
    MEMAPP_6_URL = "http://18.223.106.46:5000/"
    MEMAPP_7_URL = "http://52.15.122.5:5000/"

    # Cloudwatch metrics - use these, so we don't accidentally make doubles that cost $$$
    cloudwatch_namespace = 'ECE1779/Grp25'
    misses = 'misses'
    hits = 'hits'
    num_items_in_cache = 'number_of_items_in_cache'
    size_items_in_Megabytes = 'cache_size'
    num_active_nodes = 'num_active_nodes'
    num_posts_served = 'posts_served'
