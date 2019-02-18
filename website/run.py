import logging
import sys

import structlog
from flask import Flask, redirect, url_for
from flask_admin import Admin
from flask_qrcode import QRcode

from website.extensions import bitcoind, cache, lnd
from website.views.home_view import HomeView
from website.models import Channels, PendingChannels
from website.views.pending_channels_model_view import PendingChannelsModelView
from website.views.open_channels_model_view import OpenChannelsModelView
from website.constants import FLASK_SECRET_KEY
from website.views.request_capacity_view import RequestCapacityView


class App(Flask):
    def __init__(self):
        super().__init__(__name__)
        if __name__ != '__main__':
            gunicorn_logger = logging.getLogger('gunicorn.error')
            self.logger.handlers = gunicorn_logger.handlers
            self.logger.setLevel(gunicorn_logger.level)

        logging.basicConfig(
            format="%(message)s", stream=sys.stdout, level=logging.INFO
        )
        structlog.configure(
            processors=[
                structlog.processors.KeyValueRenderer(
                    key_order=["event", "request_id"]
                )
            ],
            context_class=structlog.threadlocal.wrap_dict(dict),
            logger_factory=structlog.stdlib.LoggerFactory(),
        )

        bitcoind.init_app(self)
        cache.init_app(self)
        lnd.init_app(self)
        QRcode(self)
        self.debug = False
        self.config['SECRET_KEY'] = FLASK_SECRET_KEY

        @self.route('/')
        @cache.memoize(timeout=600)
        def index():
            return redirect(url_for('home.index'))

        @self.errorhandler(404)
        @cache.memoize(timeout=600)
        def page_not_found(e):
            return redirect(url_for('home.index'))

        self.admin = Admin(app=self, url='/')

        home_view = HomeView(name='Home', endpoint='home')

        request_capacity_view = RequestCapacityView(
            name='Request Capacity',
            endpoint='request-capacity'
        )

        pending_channels_view = PendingChannelsModelView(
            PendingChannels,
            endpoint='pending-channels',
            name='Pending Channels',
            category='LND'
        )

        open_channels_view = OpenChannelsModelView(
            Channels,
            endpoint='channels',
            name='Open Channels',
            category='LND'
        )

        self.admin.add_view(home_view)
        self.admin.add_view(request_capacity_view)
        self.admin.add_view(pending_channels_view)
        self.admin.add_view(open_channels_view)


if __name__ == '__main__':
    app = App()
    app.debug = True
    app.run(port=5001, use_reloader=True, use_debugger=True)
