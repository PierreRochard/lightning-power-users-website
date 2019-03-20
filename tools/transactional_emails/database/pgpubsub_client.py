import json
import os
from pprint import pformat

import pgpubsub

from lnd_sql.database.session import keyring_get_or_create
from tools.transactional_emails.send_email import send_email, secure_get


def listen_thread():
    pubsub = pgpubsub.connect(
        database=keyring_get_or_create('LPU_PGDATABASE'),
        user=keyring_get_or_create('LPU_PGUSER'),
        password=keyring_get_or_create('LPU_PGPASSWORD'),
        host=os.environ.get('LPU_PGHOST', '127.0.0.1'),
        port=os.environ.get('LPU_PGPORT', '5432'),
    )
    pubsub.listen('table_update')
    while True:
        for event in pubsub.events(yield_timeouts=True):
            if event is None:
                pass
            else:
                process_message(event)


def process_message(event):
    data = json.loads(event.payload)
    # TODO: Query the table if 'row' is not in the data dictionary
    # (due to pg_notify's 8kB payload limit)

    send_email([secure_get('LPU_MAIL_USERNAME')], 'Event', pformat(data))


listen_thread()
