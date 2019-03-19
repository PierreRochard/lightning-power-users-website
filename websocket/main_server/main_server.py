import json
import ssl
from uuid import UUID

from aiohttp import web, WSMsgType
from aiohttp.web_request import Request

from lnd_grpc import lnd_grpc

from website.logger import log
from websocket.main_server.sessions.session_registry import SessionRegistry
from websocket.utilities import get_server_id


class Websocket(web.View):
    def __init__(self, request: Request):
        super().__init__(request)

        self.invoice_server_id = get_server_id('invoices')
        self.channel_server_id = get_server_id('channels')

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
                data_from_client = json.loads(msg.data)
            except:
                log.error(
                    'Error loading json',
                    exc_info=True,
                    data_string_from_client=msg.data
                )
                return

            session_id = data_from_client.get('session_id', None)
            if session_id is None:
                log.error(
                    'session_id is missing',
                    data_string_from_client=msg.data
                )
                return

            try:
                UUID(session_id, version=4)
            except ValueError:
                log.error(
                    'Invalid session_id',
                    data_string_from_client=msg.data
                )
                return

            server_id = data_from_client.get('server_id', None)

            if server_id is None:
                await self.request.app['sessions'].handle_session_message(
                    session_websocket=websocket,
                    session_id=session_id,
                    data_from_client=data_from_client
                )
                continue
            elif server_id == self.invoice_server_id:
                invoice_data = data_from_client['invoice_data']
                invoice_data['action'] = 'receive_payment'
                log.debug('emit invoice_data', invoice_data=invoice_data)
                await self.request.app['sessions'].handle_session_message(
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
                await self.request.app['sessions'].handle_session_message(
                    session_id=session_id,
                    data_from_client=message
                )
            else:
                log.error(
                    'Invalid server_id',
                    data_string_from_client=msg.data
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
    if args.sslcert:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=args.sslcert, keyfile=args.sslkey)
    else:
        ssl_context = None

    app = web.Application()
    app['grpc'] = lnd_grpc.Client(
        grpc_host=args.host,
        grpc_port=args.port,
        macaroon_path=args.macaroon,
        tls_cert_path=args.tls
    )
    app['sessions'] = SessionRegistry(app['grpc'])
    app.add_routes([web.get('/', Websocket)])

    web.run_app(app, host=args.wshost, port=8765, ssl_context=ssl_context)
    #
    # start_server = websockets.serve(ws_handler=main_server.run,
    #                                 host=args.wshost,
    #                                 port=8765)
    #
    # asyncio.get_event_loop().run_until_complete(start_server)
    # asyncio.get_event_loop().run_forever()
