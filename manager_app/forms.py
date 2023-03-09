from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, RadioField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class ManagerConfigForm(FlaskForm):
    management_mode = RadioField(
        "Management Mode",
        choices=[(0, "Manual Mode"), (1, "Automatic Mode")],
        validators=[DataRequired()]
    )
    max_miss_rate_threshold = FloatField(
        "Max Miss Rate Threshold",
        validators=[DataRequired(), NumberRange(min=0)]
    )
    min_miss_rate_threshold = FloatField(
        "Min Miss Rate Threshold",
        validators=[DataRequired(), NumberRange(min=0)]
    )
    expand_pool_ratio = FloatField(
        "Expand Pool Ratio",
        validators=[DataRequired(), NumberRange(min=0)]
    )
    shrink_pool_ratio = FloatField(
        "Shrink Pool Ratio",
        validators=[DataRequired(), NumberRange(min=0)]
    )
    submit = SubmitField("Update Configuration")
