from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# Set the RDS endpoint
rds_endpoint = "endpoint"

# Set the database credentials
db_username = "admin"
db_password = "i_am_from_beyond"
db_name = "ece"


app = Flask(__name__)

# Set the RDS endpoint
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://' + db_username + ':' + db_password + '@' + rds_endpoint # + '/' + db_name
print(app.config['SQLALCHEMY_DATABASE_URI'])

# Create the SQLAlchemy database object
db = SQLAlchemy(app)

# Try to connect to the database
try:
    with app.app_context():
        db.engine.connect()
    print("Connection to database successful!")
except Exception as e:
    print(f"Error: {e}")
