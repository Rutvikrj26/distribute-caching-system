import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://ece1779:ece1779@localhost/ece'

    # Going to RDS is as simple as changing the Database URI
    # mysql://admin:i_am_from_beyond@ece.cgdahn06kt1q.us-east-2.rds.amazonaws.com:3306/ece

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'static'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    S3_BUCKET_NAME = "your_bucket_name_here"

    # IP ADDRESSES
    FRONTEND_URL = "http://127.0.0.1:5000/"
    MANAGER_APP_URL = "http://127.0.0.1:5001/"
    MEMAPP_0_URL = "http://127.0.0.1:5002/"
    MEMAPP_1_URL = "http://127.0.0.1:5003/"
    MEMAPP_2_URL = "http://127.0.0.1:5004/"
    MEMAPP_3_URL = "http://127.0.0.1:5005/"
    MEMAPP_4_URL = "http://127.0.0.1:5006/"
    MEMAPP_5_URL = "http://127.0.0.1:5007/"
    MEMAPP_6_URL = "http://127.0.0.1:5008/"
    MEMAPP_7_URL = "http://127.0.0.1:5009/"
