import binascii
import json

import aiohttp
from aiohttp import web, WSMsgType
from aiohttp.web_request import Request
# noinspection PyPackageRequirements
from google.protobuf.json_format import MessageToDict
# noinspection PyProtectedMember
from grpc._channel import _Rendezvous
from lnd_grpc.lnd_grpc import Client

from website.logger import log
from websocket.constants import (
    MAIN_SERVER_WEBSOCKET_URL,
    INVOICES_SERVER_ID,
    CHANNELS_SERVER_ID
)


class ChannelOpeningServer(web.View):
    def __init__(self, request: Request):
        super().__init__(request)

    async def get(self):
        websocket = web.WebSocketResponse()
        await websocket.prepare(self.request)

        async for msg in websocket:
            if msg.type == WSMsgType.text:
                if msg.data == 'close':
                    await websocket.close()
                    return

            elif msg.type == WSMsgType.error:
                log.debug(
                    'ws connection closed with exception %s' % websocket.exception())
                return

            # noinspection PyBroadException
            try:
                data = json.loads(msg.data)
            except:
                log.error(
                    'Error loading json',
                    exc_info=True,
                    msgdata=msg.data
                )
                return

            if data.get('server_id', None) != INVOICES_SERVER_ID:
                log.error(
                    'Illegal access attempted',
                    msgdata=msg.data,
                    data=data
                )
                return

            log.debug('Opening channel', data=data)
            open_channel_response = self.request.app['grpc'].open_channel(
                node_pubkey_string=data['remote_pubkey'],
                local_funding_amount=int(data['local_funding_amount']),
                push_sat=0,
                sat_per_byte=int(data['sat_per_byte']),
                spend_unconfirmed=True
            )

            try:
                for update in open_channel_response:
                    update_data = MessageToDict(update)
                    if not update_data.get('chan_pending', None):
                        continue
                    txid_bytes = update.chan_pending.txid
                    txid_str = binascii.hexlify(txid_bytes[::-1]).decode('utf8')
                    update_data['chan_pending']['txid'] = txid_str
                    msg = {
                        'server_id': CHANNELS_SERVER_ID,
                        'session_id': data['session_id'],
                        'open_channel_update': update_data
                    }
                    async with aiohttp.ClientSession() as session:
                        async with session.ws_connect(
                                MAIN_SERVER_WEBSOCKET_URL) as m_ws:
                            await m_ws.send_str(json.dumps(msg))
                    break
            except _Rendezvous as e:
                error_details = e.details()
                error_message = {
                    'server_id': CHANNELS_SERVER_ID,
                    'session_id': data['session_id'],
                    'error': error_details
                }
                log.error('Open channel error', error_message=error_message)
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(
                            MAIN_SERVER_WEBSOCKET_URL) as m_ws:
                        await m_ws.send_str(json.dumps(error_message))


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Channel opening websocket server'
    )

    parser.add_argument(
        '--macaroon',
        '-m',
        type=str,
        default=None
    )

    parser.add_argument(
        '--tls',
        '-t',
        type=str,
        default=None
    )

    parser.add_argument(
        '--port',
        type=str,
        help='Port for gRPC',
        default='10009'
    )

    parser.add_argument(
        '--host',
        type=str,
        help='Host IP address for gRPC',
        default='127.0.0.1'
    )

    args = parser.parse_args()

    app = web.Application()
    app['grpc'] = Client(
        grpc_host=args.host,
        grpc_port=args.port,
        macaroon_path=args.macaroon,
        tls_cert_path=args.tls
    )

    app.add_routes([web.get('/', ChannelOpeningServer)])

    web.run_app(app, host='localhost', port=8710)
