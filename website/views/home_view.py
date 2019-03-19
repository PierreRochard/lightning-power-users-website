import uuid

from bitcoin.core import COIN
from flask import render_template, session
from flask_admin import BaseView, expose

from lnd_sql import session_scope
from lnd_sql.models import ExchangeRates
from website.constants import EXPECTED_BYTES
from website.forms.request_capacity_form import get_request_capacity_form
from websocket.constants import MAIN_SERVER_WEBSOCKET_URL


class HomeView(BaseView):
    @expose('/')
    def index(self):
        with session_scope() as db_session:
            last_price = (
                db_session.query(ExchangeRates.last)
                .order_by(ExchangeRates.timestamp.desc())
                .limit(1)
                .scalar()
            )
        price_per_sat = last_price / COIN
        form = get_request_capacity_form()

        if session.get('session_id', None) is None:
            session['session_id'] = uuid.uuid4().hex
        if session.get('session_id', None) is None:
            session['session_id'] = uuid.uuid4().hex
        return render_template(
            'home_view/index.html',
            WEBSOCKET_HOST=MAIN_SERVER_WEBSOCKET_URL,
            form=form,
            price_per_sat=price_per_sat,
            EXPECTED_BYTES=EXPECTED_BYTES
        )
