import uuid

import structlog
from bitcoin.core import COIN
from flask import render_template, session
from flask_admin import BaseView, expose

from website.constants import EXPECTED_BYTES
from website.forms.request_capacity_form import get_request_capacity_form
from website.utilities.cache.cache import get_latest
from websocket.constants import DEFAULT_WEBSOCKET_URL


class HomeView(BaseView):
    @expose('/')
    def index(self):
        logger = structlog.get_logger()
        log = logger.new(request_id=str(uuid.uuid4()))
        price = get_latest('usd_price')
        last_price = price['last']
        price_per_sat = last_price / COIN
        form = get_request_capacity_form()

        if session.get('session_id', None) is None:
            session['session_id'] = uuid.uuid4().hex
        if session.get('session_id', None) is None:
            session['session_id'] = uuid.uuid4().hex
        return render_template(
            'home_view/index.html',
            WEBSOCKET_HOST=DEFAULT_WEBSOCKET_URL,
            form=form,
            price_per_sat=price_per_sat,
            EXPECTED_BYTES=EXPECTED_BYTES
        )
