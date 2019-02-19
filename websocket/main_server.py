import asyncio
import json
from uuid import UUID

import websockets

from lnd_grpc import lnd_grpc
from lnd_grpc.lnd_grpc import Client
from website.logger import log
from websocket.models.channel_opening_invoices import ChannelOpeningInvoices
from websocket.models.users import Users
from websocket.utilities import get_server_id


class MainServer(object):
    rpc: Client

    def __init__(self, lnd_dir: str = None,
                 lnd_network: str = 'mainnet',
                 lnd_grpc_host: str = 'localhost',
                 lnd_grpc_port: str = '10011'):
        self.rpc = lnd_grpc.Client(
            lnd_dir=lnd_dir,
            network=lnd_network,
            grpc_host=lnd_grpc_host,
            grpc_port=lnd_grpc_port,
        )
        self.channel_opening_invoices = ChannelOpeningInvoices()
        self.users = Users(self.rpc)
        self.channel_opening_server = None

    async def run(self, websocket, path):
        while True:
            data_string_from_client = await websocket.recv()

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

            user_id = data_from_client.get('user_id', None)
            server_id = data_from_client.get('server_id', None)
            if not user_id and not server_id:
                log.error(
                    'user_id and server_id missing',
                    data_string_from_client=data_string_from_client
                )
                return
            if server_id is not None and server_id not in [
                get_server_id('main'),
                get_server_id('invoices'),
                get_server_id('channels'),
                get_server_id('webapp')
            ]:
                log.error(
                    'Invalid server_id',
                    data_string_from_client=data_string_from_client
                )
                return
            try:
                UUID(user_id, version=4)
            except ValueError:
                log.error(
                    'Invalid user_id',
                    data_string_from_client=data_string_from_client
                )
                return

            # User registration
            if user_id and not server_id:
                await self.users.register(
                    user_id=user_id,
                    websocket=websocket
                )
                if data_from_client.get('action', None) == 'connect':
                    log.debug('connect', data_from_client=data_from_client)
                    form_data = data_from_client.get('form_data', None)
                    form_data_pubkey = [f for f in form_data if f['name'] == 'pubkey'][0]
                    if not len(form_data_pubkey):
                        log.debug(
                            'Connect did not include valid form data',
                            data_from_client=data_from_client
                        )
                        continue
                    pubkey = form_data_pubkey.get('value', '').strip()
                    await self.users.connect_to_peer(user_id, pubkey)

                continue

            # Server action dispatching
            data_from_server = data_from_client
            if server_id == get_server_id('webapp'):
                if data_from_server['type'] == 'inbound_capacity_request':
                    self.channel_opening_invoices.add_invoice_package(
                        r_hash=data_from_server['invoice']['r_hash'],
                        package=data_from_server
                    )
                    log.debug(
                        'Received from server',
                        data_type='inbound_capacity_request'
                    )
                    return

            elif server_id == get_server_id('invoices'):
                invoice_data = data_from_server['invoice_data']
                package = self.channel_opening_invoices.get_invoice_package(
                    r_hash=invoice_data['r_hash']
                )
                if package is None:
                    log.debug(
                        'r_hash not found in channel_opening_invoices',
                        invoice_data=invoice_data
                    )
                    return

                log.debug('emit invoice_data', invoice_data=invoice_data)
                await self.users.send(
                    package['user_id'],
                    invoice_data
                )

                if package.get('reciprocation_capacity', None):
                    local_funding_amount = package['reciprocation_capacity']
                else:
                    local_funding_amount = int(package['form_data']['capacity'])

                sat_per_byte = int(package['form_data']['transaction_fee_rate'])
                data = dict(
                    server_id=get_server_id('main'),
                    user_id=package['user_id'],
                    type='open_channel',
                    remote_pubkey=package['parsed_pubkey'],
                    local_funding_amount=local_funding_amount,
                    sat_per_byte=sat_per_byte
                )
                await self.channel_opening_server.send(json.dumps(data))

            elif server_id == get_server_id('channels'):
                self.channel_opening_server = websocket
                message = {
                    'error': data_from_server.get('error', None),
                    'open_channel_update': data_from_server.get(
                        'open_channel_update', None)
                }
                await self.users.send(
                    user_id=user_id,
                    message=message
                )


if __name__ == '__main__':
    main_server = MainServer()
    start_server = websockets.serve(main_server.run, 'localhost', 8765)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
