import json
import os
from datetime import datetime

import humanize
from flask import render_template
from flask_admin import BaseView, expose
# noinspection PyPackageRequirements
from google.protobuf.json_format import MessageToDict

from website.constants import CACHE_PATH
from website.extensions import cache, lnd
from website.logger import log


class HomeView(BaseView):
    @expose('/')
    # @cache.memoize(timeout=600)
    def index(self):

        # noinspection PyBroadException
        info_cache_file = os.path.join(CACHE_PATH, 'info.json')
        try:
            get_info_response = lnd.rpc.get_info()
            info = MessageToDict(get_info_response)
            best_header_timestamp = int(info['best_header_timestamp'])
            best_header_datetime = datetime.fromtimestamp(best_header_timestamp)
            best_header_strftime = best_header_datetime.strftime('%c')
            best_header_humanized = humanize.naturaltime(best_header_datetime)
            info['best_header_timestamp'] = f'{best_header_strftime} ({best_header_humanized})'
            with open(info_cache_file, 'w') as f:
                json.dump(info, f)
        except:
            log.error(
                'HomeView.index exception',
                exc_info=True
            )
            try:
                with open(info_cache_file, 'r') as f:
                    info = json.load(f)
            except FileNotFoundError:
                info = {}
            raise

        return render_template('index.html', info=info)
