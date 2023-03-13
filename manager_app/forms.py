from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, RadioField, SubmitField, SelectField, IntegerField
from wtforms.validators import DataRequired, NumberRange
from wtforms.validators import DataRequired, InputRequired, Optional

class MemcacheConfigForm(FlaskForm):
    # Define the form here to change memcache configuration
    policy = RadioField('Replacement Policy:', choices=[(1, 'Random Replacement'), (0, 'Least Recently Used')], validators=[DataRequired()])
    capacity = IntegerField('Memcache capacity (in MB):', validators=[InputRequired()])
    clear_cache = BooleanField('Clear All Keys from Cache?')
    submit = SubmitField('Submit')

class ManagerConfigForm(FlaskForm):
    management_mode = RadioField('Management Mode :', choices=[(1, 'Automatic'), (0, 'Manual')], validators=[DataRequired()])
    # optional form fields - for Automatic mode
    max_miss_rate_threshold = FloatField('Max Miss Rate Threshold', validators=[NumberRange(min=0.0, max=1.0)])
    min_miss_rate_threshold = FloatField('Min Miss Rate Threshold', validators=[NumberRange(min=0.0, max=1.0)])
    expand_pool_ratio = FloatField('Expand Pool Ratio', validators=[NumberRange(min=1.0, max=8.0)])
    shrink_pool_ratio = FloatField('Shrink Pool Ratio', validators=[NumberRange(min=0.1, max=1.0)])
    # optional form fields - for Manual mode
    grow_pool = SubmitField('Grow Pool')
    shrink_pool = SubmitField('Shrink Pool')
    # final submit button
    submit = SubmitField('Submit')

    def validate(self, extra_validators=None):
        """
        Validate the form.

        :return: bool indicating if the form is valid
        """
        # Call parent validate method
        rv = FlaskForm.validate(self)

        if not rv:
            return False

        if self.management_mode.data:
            if self.max_miss_rate_threshold.data is None or self.min_miss_rate_threshold.data is None \
                    or self.expand_pool_ratio.data is None or self.shrink_pool_ratio.data is None:
                self.max_miss_rate_threshold.errors.append('All fields are required in automatic mode.')
                self.min_miss_rate_threshold.errors.append('All fields are required in automatic mode.')
                self.expand_pool_ratio.errors.append('All fields are required in automatic mode.')
                self.shrink_pool_ratio.errors.append('All fields are required in automatic mode.')
                return False
            elif self.max_miss_rate_threshold.data <= self.min_miss_rate_threshold.data:
                self.max_miss_rate_threshold.errors.append('Max miss rate threshold must be greater than min miss rate threshold.')
                return False
        return True

