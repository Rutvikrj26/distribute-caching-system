from frontend import frontend, db
from frontend.models import Image


@frontend.shell_context_processor
def make_shell_context():
    return {'db': db, 'Image': Image}
