import time

# noinspection PyProtectedMember
from google.protobuf.json_format import MessageToDict
from grpc._channel import _Rendezvous
# noinspection PyPackageRequirements
from googleapiclient.discovery import build
# noinspection PyPackageRequirements
from httplib2 import Http
from oauth2client import file, client, tools

from lnd_grpc.protos.rpc_pb2 import OpenStatusUpdate
from tools.node import Node
from tools.secrets import spreadsheet_id
from website.logger import log

SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
SAMPLE_RANGE_NAME = 'Form Responses 1!A1:J'


def get_google_sheet_data(node_operator):
    store = file.Storage('token.json')
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets('credentials.json', SCOPES)
        credentials = tools.run_flow(flow, store)
    service = build('sheets', 'v4', http=credentials.authorize(Http()))

    sheet = service.spreadsheets()
    result = sheet.values().get(spreadsheetId=spreadsheet_id,
                                range=SAMPLE_RANGE_NAME).execute()
    values = result.get('values', [])

    if not values:
        log.info('No data found.')
    else:
        total = 0
        for index, row in enumerate(values[1:]):
            old_row = row[3:]
            pubkey = row[1].split('@')[0]
            log.debug('pubkey', pubkey=pubkey)
            # twitter_handle = row.get(2)
            if pubkey in node_operator.nodes:
                node: Node = node_operator.nodes[pubkey]
                active_channels = [c for c in node.channels if c.is_active or c.is_pending]
                txids = [c.channel_point for c in active_channels]
                new_row = [
                    len(node.channels),
                    node.remote_balance,
                    node.local_balance,
                    node.available_capacity,
                    node.balance,
                    ', '.join(txids)
                ]
                status = ''
                if len(active_channels) == 1 and active_channels[0].remote_balance:
                    capacity = active_channels[0].remote_balance
                    log.debug('Opening a channel',
                              pubkey=node.pubkey,
                              capacity="{0:,d}".format(capacity))
                    open_channel_updates = node_operator.rpc.open_channel(
                        node_pubkey_string=node.pubkey,
                        local_funding_amount=max(capacity, 200000),
                        push_sat=0,
                        sat_per_byte=1,
                        spend_unconfirmed=True
                    )
                    try:
                        for open_channel_update in open_channel_updates:
                            log.debug('open_channel_update',
                                      open_channel_update=MessageToDict(open_channel_update))
                            if isinstance(open_channel_update, OpenStatusUpdate):
                                status = 'Pending channel'
                                break
                    except _Rendezvous as e:
                        log.debug('open_channel exception', details=e.details())
                        status = e.details()
                new_row.append(status)
            else:
                new_row = [
                    0,
                    0,
                    0,
                    0,
                    0,
                    ''
                ]
            changed = False
            for i, _ in enumerate(new_row[:-2]):
                try:
                    if old_row[i] == '':
                        old_row[i] = 0
                    old_value = int(float(str(old_row[i]).replace(',', '')))
                except IndexError:
                    old_value = 0

                if new_row[i] is not None and int(new_row[i]) != old_value:
                    changed = True
                    break
            if changed or True:
                body = dict(values=[new_row])
                try:
                    result = service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f'Form Responses 1!D{index + 2}:J',
                        body=body,
                        valueInputOption='USER_ENTERED').execute()
                    time.sleep(0.5)
                except Exception as e:
                    log.debug('spreadsheet error', exc_info=True)
                    pass
