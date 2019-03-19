import asyncio
import json
import ssl
from uuid import UUID

import websockets

from lnd_grpc import lnd_grpc
from lnd_grpc.lnd_grpc import Client

from website.logger import log
from websocket.main_server.sessions.session_registry import SessionRegistry
from websocket.utilities import get_server_id


class MainServer(object):
    rpc: Client

    def __init__(self, grpc_host, grpc_port, tls_cert_path, macaroon_path):
        self.rpc = lnd_grpc.Client(
            grpc_host=grpc_host,
            grpc_port=grpc_port,
            tls_cert_path=tls_cert_path,
            macaroon_path=macaroon_path
        )
        self.invoice_server_id = get_server_id('invoices')
        self.channel_server_id = get_server_id('channels')
        self.sessions = SessionRegistry(self.rpc)

    async def run(self, websocket, path):
        async for data_string_from_client in websocket:
            # noinspection PyBroadException
            try:
                data_from_client = json.loads(data_string_from_client)
            except:
                log.error(
                    'Error loading json',
                    exc_info=True,
                    data_string_from_client=data_string_from_client
                )
                return

            session_id = data_from_client.get('session_id', None)
            if session_id is None:
                log.error(
                    'session_id is missing',
                    data_string_from_client=data_string_from_client
                )
                return

            try:
                UUID(session_id, version=4)
            except ValueError:
                log.error(
                    'Invalid session_id',
                    data_string_from_client=data_string_from_client
                )
                return

            server_id = data_from_client.get('server_id', None)

            if server_id is None:
                await self.sessions.handle_session_message(
                    session_websocket=websocket,
                    session_id=session_id,
                    data_from_client=data_from_client
                )
                continue
            elif server_id == self.invoice_server_id:
                invoice_data = data_from_client['invoice_data']
                invoice_data['action'] = 'receive_payment'
                log.debug('emit invoice_data', invoice_data=invoice_data)
                await self.sessions.handle_session_message(
                    session_id=data_from_client['session_id'],
                    data_from_client=invoice_data
                )
            elif server_id == self.channel_server_id:
                message = {
                    'error': data_from_client.get('error', None),
                    'open_channel_update': data_from_client.get(
                        'open_channel_update', None),
                    'action': 'channel_open'
                }
                await self.sessions.handle_session_message(
                    session_id=session_id,
                    data_from_client=message
                )
            else:
                log.error(
                    'Invalid server_id',
                    data_string_from_client=data_string_from_client
                )
                return


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Main websocket server'
    )

    parser.add_argument(
        '--macaroon',
        '-m',
        type=str
    )

    parser.add_argument(
        '--tls',
        '-t',
        type=str
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

    parser.add_argument(
        '--sslcert',
        type=str,
        help='Path for WS SSL cert',
        default=None
    )

    parser.add_argument(
        '--sslkey',
        type=str,
        help='Path for WS SSL key',
        default=None
    )

    parser.add_argument(
        '--wshost',
        type=str,
        help='Host for WS',
        default='localhost'
    )

    args = parser.parse_args()
    main_server = MainServer(
        grpc_host=args.host,
        grpc_port=args.port,
        macaroon_path=args.macaroon,
        tls_cert_path=args.tls
    )
    if args.ssl:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=args.sslcert, keyfile=args.sslkey)
    else:
        ssl_context = None

    start_server = websockets.serve(ws_handler=main_server.run,
                                    host=args.wshost,
                                    port=8765)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
