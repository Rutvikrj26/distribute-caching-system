from memapp import db
from datetime import datetime


class MemcacheConfig(db.Model):


    def __repr__(self):
        return '<MemcacheData with ID: {0}>'.format(self.id)


class BadExtensionException(Exception):
    """Raised when the image file being uploaded is not one of the valid extensions in Config.ALLOWED_EXTENSIONS"""
    pass
