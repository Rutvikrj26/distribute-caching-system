from memapp import db
from datetime import datetime


class PoolConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    max_threshold = db.Column(db.Float)
    min_threshold = db.Column(db.Float)
    expand_ratio = db.Column(db.Float)
    shrink_ratio = db.Column(db.Float)

class BadExtensionException(Exception):
    """Raised when the image file being uploaded is not one of the valid extensions in Config.ALLOWED_EXTENSIONS"""
    pass
