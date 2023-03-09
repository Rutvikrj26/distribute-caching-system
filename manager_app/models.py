from datetime import datetime
from app import db

class ManagerConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    management_mode = db.Column(db.Boolean, default=True)
    max_miss_rate_threshold = db.Column(db.Float, default=0.2)
    min_miss_rate_threshold = db.Column(db.Float, default=0.1)
    expand_pool_ratio = db.Column(db.Float, default=1.5)
    shrink_pool_ratio = db.Column(db.Float, default=0.5)
    manual_pool_size = db.Column(db.Integer, default=1)

    def __repr__(self):
        return f"ManagerConfig(management_mode={self.management_mode}, max_miss_rate_threshold={self.max_miss_rate_threshold}, min_miss_rate_threshold={self.min_miss_rate_threshold}, expand_pool_ratio={self.expand_pool_ratio}, shrink_pool_ratio={self.shrink_pool_ratio}, manual_pool_size={self.manual_pool_size})"

