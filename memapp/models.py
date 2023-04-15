#from memapp import db
from datetime import datetime


# class MemcacheData(db.Model):
#     timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, primary_key=True)
#     hits = db.Column(db.Integer)
#     misses = db.Column(db.Integer)
#     posts_served = db.Column(db.Integer)
#     num_items = db.Column(db.Integer)
#     current_size = db.Column(db.Float)
#
#     def __repr__(self):
#         return '<MemcacheData with ID: {0}>'.format(self.id)


class BadExtensionException(Exception):
    """Raised when the image file being uploaded is not one of the valid extensions in Config.ALLOWED_EXTENSIONS"""
    pass
