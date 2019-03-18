import asyncio
import codecs
import json

# noinspection PyPackageRequirements
from google.protobuf.json_format import MessageToDict
# noinspection PyProtectedMember
from grpc._channel import _Rendezvous
import websockets

from lnd_grpc import lnd_grpc
from lnd_grpc.lnd_grpc import Client
from website.logger import log
from websocket.constants import MAIN_SERVER_WEBSOCKET_URL
from websocket.utilities import get_server_id


class ChannelOpeningServer(object):
    rpc: Client

    def __init__(self, grpc_host, grpc_port, tls_cert_path, macaroon_path):
        self.rpc = lnd_grpc.Client(
            grpc_host=grpc_host,
            grpc_port=grpc_port,
            tls_cert_path=tls_cert_path,
            macaroon_path=macaroon_path
        )

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

        if data.get('server_id', None) != get_server_id('invoices'):
            log.error(
                'Illegal access attempted',
                data_string_from_client=data_string_from_client,
                data=data
            )
            return

        log.debug('Opening channel', data=data)
        open_channel_response = self.rpc.open_channel(
            timeout=4,
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
                hex_txid = codecs.encode(update.chan_pending.txid, 'hex')
                str_txid = codecs.decode(hex_txid, 'utf-8')
                update_data['chan_pending']['txid'] = str_txid
                msg = {
                    'server_id': get_server_id('channels'),
                    'session_id': data['session_id'],
                    'open_channel_update': update_data
                }
                async with websockets.connect(
                        MAIN_SERVER_WEBSOCKET_URL) as m_ws:
                    await m_ws.send(json.dumps(msg))
                break
        except _Rendezvous as e:
            error_details = e.details()
            error_message = {
                'server_id': get_server_id('channels'),
                'session_id': data['session_id'],
                'error': error_details
            }
            log.error('Open channel error', error_message=error_message)
            async with websockets.connect(
                    MAIN_SERVER_WEBSOCKET_URL) as m_ws:
                await m_ws.send(json.dumps(error_message))


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
    main_server = ChannelOpeningServer(
        grpc_host=args.host,
        grpc_port=args.port,
        macaroon_path=args.macaroon,
        tls_cert_path=args.tls
    )
    start_server = websockets.serve(main_server.run, 'localhost', 8710)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
