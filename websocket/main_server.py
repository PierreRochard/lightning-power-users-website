import asyncio
import json
from uuid import UUID

import websockets
from sqlalchemy.orm.exc import NoResultFound

from lnd_grpc import lnd_grpc
from lnd_grpc.lnd_grpc import Client
from lnd_sql import session_scope
from lnd_sql.models import InboundCapacityRequest

from website.logger import log
from websocket.models.channel_opening_invoices import ChannelOpeningInvoices
from websocket.sessions.session_registry import SessionRegistry
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
        self.channel_opening_invoices = ChannelOpeningInvoices()
        self.sessions = SessionRegistry(self.rpc)
        self.channel_opening_server = None

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
                with session_scope() as session:
                    try:
                        inbound_capacity_request: InboundCapacityRequest = (
                            session.query(InboundCapacityRequest)
                            .filter(InboundCapacityRequest.invoice_r_hash == invoice_data['r_hash'])
                            .one()
                        )
                    except NoResultFound:
                        log.debug(
                            'r_hash not found in inbound_capacity_request table',
                            data_from_client=data_from_client
                        )
                        continue

                    if int(invoice_data['amt_paid_sat']) != inbound_capacity_request.total_fee:
                        log.error('Payment does not match liability',
                                  invoice_data=invoice_data,
                                  total_fee=inbound_capacity_request.total_fee)
                        continue

                    log.debug('emit invoice_data', invoice_data=invoice_data)
                    await self.sessions.handle_session_message(
                        session_id=inbound_capacity_request.session_id,
                        data_from_client=invoice_data
                    )

                    data = dict(
                        server_id=get_server_id('main'),
                        session_id=inbound_capacity_request.session_id,
                        type='open_channel',
                        remote_pubkey=inbound_capacity_request.remote_pubkey,
                        local_funding_amount=inbound_capacity_request.capacity,
                        sat_per_byte=inbound_capacity_request.transaction_fee_rate
                    )
                await self.channel_opening_server.send(json.dumps(data))

            elif server_id == self.channel_server_id:
                self.channel_opening_server = websocket
                message = {
                    'error': data_from_client.get('error', None),
                    'open_channel_update': data_from_client.get(
                        'open_channel_update', None)
                }
                await self.sessions.send(
                    session_id=session_id,
                    message=message
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

    args = parser.parse_args()
    main_server = MainServer(
        grpc_host=args.host,
        grpc_port=args.port,
        macaroon_path=args.macaroon,
        tls_cert_path=args.tls
    )
    start_server = websockets.serve(main_server.run, 'localhost', 8765)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
