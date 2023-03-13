from frontend import db
from datetime import datetime


class Image(db.Model):
    id = db.Column(db.String(120), primary_key=True)
    value = db.Column(db.String(256), index=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    def __repr__(self):
        return '<Image with key: {0} and value: {1}>'.format(self.key, self.value)
