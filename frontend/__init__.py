from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bootstrap import Bootstrap


frontend = Flask(__name__)
frontend.config.from_object(Config)
db = SQLAlchemy(frontend)

migrate = Migrate(frontend, db)
bootstrap = Bootstrap(frontend)

from frontend import routes, models
from frontend.models import MemcacheConfig

with frontend.app_context():
    db.create_all()
    current_memcache_configs = MemcacheConfig.query.all()
    for config in current_memcache_configs:
        db.session.delete(config)
    db.session.commit()
    initial_memcache_config = MemcacheConfig(id=1, isRandom=1, maxSize=2)
    db.session.add(initial_memcache_config)
    db.session.commit()
