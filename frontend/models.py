# from frontend import db
from datetime import datetime
from frontend import db, login_manager
from flask_login import UserMixin

# class Image(db.Model):
#     id = db.Column(db.String(120), primary_key=True)
#     value = db.Column(db.String(256), index=True)
#     timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
#
#     def __repr__(self):
#         return '<Image with key: {0} and value: {1}>'.format(self.key, self.value)


# class MemcacheConfig(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     isRandom = db.Column(db.Integer)
#     maxSize = db.Column(db.Integer)
#
#     def __repr__(self):
#         return '<MemcacheConfig with ID: {0}>'.format(self.id)

