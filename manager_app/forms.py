from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, RadioField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class ManagerConfigForm(FlaskForm):
    management_mode = RadioField('Management Mode', choices=[('True', 'Automatic'), ('False', 'Manual')], validators=[DataRequired()])
    # optional form fields
    max_miss_rate_threshold = FloatField('Max Miss Rate Threshold', validators=[NumberRange(min=0.0, max=1.0)])
    min_miss_rate_threshold = FloatField('Min Miss Rate Threshold', validators=[NumberRange(min=0.0, max=1.0)])
    expand_pool_ratio = FloatField('Expand Pool Ratio', validators=[NumberRange(min=1.0, max=8.0)])
    shrink_pool_ratio = FloatField('Shrink Pool Ratio', validators=[NumberRange(min=0.1, max=1.0)])
    grow_pool = SubmitField('Grow Pool')
    shrink_pool = SubmitField('Shrink Pool')

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
        else:
            if not (self.grow_pool.data ^ self.shrink_pool.data):
                self.grow_pool.errors.append('You can only grow or shrink pool at a time.')
                self.shrink_pool.errors.append('You can only grow or shrink pool at a time.')
                return False

        return True

