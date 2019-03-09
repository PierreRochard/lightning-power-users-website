from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField
from wtforms.validators import DataRequired
from wtforms.widgets import TextArea

from website.constants import CAPACITY_CHOICES, CAPACITY_FEE_RATES
from website.utilities.cache.cache import get_latest


class RequestCapacityForm(FlaskForm):
    pub_key = StringField(
        'Your PubKey',
        render_kw={'placeholder': 'pubkey \nor \npubkey@host:port'},
        validators=[DataRequired()],
        widget=TextArea()
    )
    twitter_username = StringField('Twitter Username (Optional)')
    email_address = StringField('E-mail Address (Optional)')
    transaction_fee_rate = SelectField('Average Channel Opening Speed')
    capacity = SelectField('Capacity')
    capacity_fee_rate = SelectField('Minimum Time Open')
    request_capacity = SubmitField('Request Capacity')


def get_request_capacity_form() -> RequestCapacityForm:
    form = RequestCapacityForm()
    fee_estimates = get_latest('fee_estimate')

    fee_estimate_choices = []
    previous_estimate = 0
    for fee_estimate in fee_estimates:
        estimated_fee_per_byte = fee_estimate['conservative']['feerate']
        if estimated_fee_per_byte == previous_estimate:
            continue
        previous_estimate = estimated_fee_per_byte
        select_label_time_estimate = fee_estimate['label'].replace('_',
                                                                   ' ').capitalize()
        if estimated_fee_per_byte > 1:
            select_label = f'{select_label_time_estimate} ({estimated_fee_per_byte} sats per byte)'
        else:
            select_label = f'{select_label_time_estimate} (1 sat per byte)'
        select_value = estimated_fee_per_byte
        fee_estimate_choices.append((select_value, select_label))

    form.transaction_fee_rate.choices = fee_estimate_choices
    form.capacity.choices = []
    form.capacity.choices.append((0, 'Reciprocate'))
    for capacity_choice in CAPACITY_CHOICES:
        form.capacity.choices.append((capacity_choice, f'{capacity_choice:,}'))

    form.capacity_fee_rate.choices = CAPACITY_FEE_RATES
    return form
