from datetime import datetime
from app import db

class ManagerConfig(db.Model):
    __tablename__ = 'manager_config'
    id = db.Column(db.Integer, primary_key=True)
    management_mode = db.Column(db.Boolean, default=False)
    max_miss_rate_threshold = db.Column(db.Float, default=0.5)
    min_miss_rate_threshold = db.Column(db.Float, default=0.2)
    expand_pool_ratio = db.Column(db.Float, default=0.5)
    shrink_pool_ratio = db.Column(db.Float, default=0.5)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ManagerConfig management_mode={self.management_mode} max_miss_rate_threshold={self.max_miss_rate_threshold} min_miss_rate_threshold={self.min_miss_rate_threshold} expand_pool_ratio={self.expand_pool_ratio} shrink_pool_ratio={self.shrink_pool_ratio} last_updated={self.last_updated}>'

