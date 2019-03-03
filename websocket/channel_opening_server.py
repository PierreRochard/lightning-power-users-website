import json

from google.protobuf.json_format import MessageToDict
from grpc._channel import _Rendezvous

from lnd_grpc import lnd_grpc
from website.logger import log
from websocket.utilities import get_server_id


class ChannelOpeningServer(object):
    def __init__(self):
        pass

    async def run(self, websocket, path):
        data_string_from_client = await websocket.recv()
        # noinspection PyBroadException
        try:
            data = json.loads(data_string_from_client)
        except:
            log.error(
                'Error loading json',
                exc_info=True,
                data_string_from_client=data_string_from_client
            )
            return

        if data.get('server_id', None) != get_server_id('main'):
            log.error(
                'Illegal access attempted',
                data_string_from_client=data_string_from_client,
                data=data
            )
            return

        log.debug('Opening channel', data=data)
        open_channel_response = lnd_grpc.Client().open_channel(
            node_pubkey_string=data['remote_pubkey'],
            local_funding_amount=int(data['local_funding_amount']),
            push_sat=0,
            sat_per_byte=int(data['sat_per_byte']),
            spend_unconfirmed=True
        )

        try:
            for update in open_channel_response:
                update_data = MessageToDict(update)
                msg = {
                    'server_id': get_server_id('channels'),
                    'session_id': data['session_id'],
                    'open_channel_update': update_data
                }
                await websocket.send(json.dumps(msg))
                if update_data.get('chan_pending', None):
                    break
        except _Rendezvous as e:
            error_details = e.details()
            error_message = {
                'server_id': get_server_id('channels'),
                'session_id': data['session_id'],
                'error': error_details
            }
            log.error('Open channel error', error_message=error_message)
            await websocket.send(error_message)
