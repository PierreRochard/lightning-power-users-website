import asyncio
import json

# noinspection PyProtectedMember
from grpc._channel import _Rendezvous
from google.protobuf.json_format import MessageToDict
import websockets

from node_launcher.logging import log
from tools.lnd_client import lnd_remote_client
from websocket.models.channel_opening_invoices import ChannelOpeningInvoices
from websocket.models.users import Users
from websocket.utilities import get_server_key


class MainServer(object):
    def __init__(self):
        self.channel_opening_invoices = ChannelOpeningInvoices()
        self.users = Users()

    async def run(self, websocket, path):
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

        tracker = data_from_client.get('tracker', None)
        if not tracker:
            return

        if tracker not in [
            get_server_key('main'),
            get_server_key('invoices'),
            get_server_key('channels'),
            get_server_key('webapp')
        ]:
            await self.users.register(
                tracker=tracker,
                websocket=websocket
            )
            return

        data_from_server = data_from_client
        if data_from_server['type'] == 'inbound_capacity_request':
            self.channel_opening_invoices.add_invoice_package(
                r_hash=data_from_server['invoice']['r_hash'],
                package=data_from_server
            )
            log.debug('Received from server', data_from_server=data_from_server)
            return
        elif data_from_server['type'] == 'invoice_paid':
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
            await self.users.notify_user(
                package['tracker'],
                invoice_data
            )

            if package.get('reciprocation_capacity', None):
                local_funding_amount = package['reciprocation_capacity']
            else:
                local_funding_amount = int(package['form_data']['capacity'])

            sat_per_byte = int(package['form_data']['transaction_fee_rate'])

            response = lnd_remote_client.open_channel(
                node_pubkey_string=package['parsed_pubkey'],
                local_funding_amount=local_funding_amount,
                push_sat=0,
                sat_per_byte=sat_per_byte,
                spend_unconfirmed=True
            )

            try:
                for update in response:
                    update_data = MessageToDict(update)
                    msg = {'open_channel_update': update_data}
                    await self.users.notify_user(
                        package['tracker'],
                        msg
                    )
                    if update_data.get('chan_pending', None):
                        break
            except _Rendezvous as e:
                error_details = e.details()
                error_message = {'error': error_details}
                await self.users.notify_user(
                    package['tracker'],
                    error_message
                )


if __name__ == '__main__':
    main_server = MainServer()
    start_server = websockets.serve(main_server.run, 'localhost', 8765)

    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
