import uuid

from flask import render_template, session
from flask_admin import BaseView, expose

from websocket.constants import DEFAULT_WEBSOCKET_URL


class HomeView(BaseView):
    @expose('/')
    def index(self):
        if session.get('user_id', None) is None:
            session['user_id'] = uuid.uuid4().hex
        return render_template('home_view.html', WEBSOCKET_HOST=DEFAULT_WEBSOCKET_URL)
