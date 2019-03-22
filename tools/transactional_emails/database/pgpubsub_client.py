import json
import os

import pgpubsub
from jinja2 import Template
from premailer import transform

from lnd_sql.database.session import keyring_get_or_create
from tools.transactional_emails.send_email import send_email, secure_get

templates_directory = os.path.abspath(__file__ + "/../../templates")

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

    if data['table_name'] == 'public.inbound_capacity_request':
        subject = f'{data["row"]["session_id"]} {data["row"]["status"]}'
    else:
        subject = data['table_name']

    html_body = dict_to_email_template(
        title=data["row"].get('status', None),
        table_caption=data["row"].get('status', None),
        table_data=data["row"]
    )

    send_email(recipients=[secure_get('LPU_MAIL_USERNAME')],
               subject=subject, html_body=html_body)


def dict_to_email_template(title, table_caption, table_data):
    email_template = os.path.join(templates_directory, 'email_template.html')
    with open(email_template, 'r') as html_template:
        html_template_string = html_template.read()

    css_template = os.path.join(templates_directory, 'styles.css')
    with open(css_template, 'r') as css:
        css_string = css.read()

    template = Template(html_template_string)

    html_body = template.render(title=title,
                                css=css_string,
                                table_caption=table_caption,
                                table_data=table_data)

    return transform(html_body)

listen_thread()
