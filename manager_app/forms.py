from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, RadioField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class ManagerConfigForm(FlaskForm):
    management_mode = BooleanField('Management Mode', validators=[DataRequired()])
    max_miss_rate_threshold = FloatField('Max Miss Rate Threshold', validators=[Optional()])
    min_miss_rate_threshold = FloatField('Min Miss Rate Threshold', validators=[Optional()])
    expand_pool_ratio = FloatField('Expand Pool Ratio', validators=[Optional()])
    shrink_pool_ratio = FloatField('Shrink Pool Ratio', validators=[Optional()])
    grow_pool = SubmitField('Grow Pool')
    shrink_pool = SubmitField('Shrink Pool')

    def validate(self):
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

