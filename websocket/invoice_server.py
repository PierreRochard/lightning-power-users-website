import asyncio
import json
import signal

import aiohttp
from google.protobuf.json_format import MessageToDict


from lnd_grpc.lnd_grpc import Client
from lnd_sql.scripts.upsert_invoices import UpsertInvoices
from website.logger import log
from websocket.constants import (
    CHANNEL_OPENING_SERVER_WEBSOCKET_URL,
    MAIN_SERVER_WEBSOCKET_URL
)
from websocket.queries import InboundCapacityRequestQueries
from websocket.utilities import get_server_id


class InvoiceServer(object):
    def __init__(self, rpc: Client):
        self.rpc = rpc

    @staticmethod
    async def handle_invoice(local_pubkey, invoice):
        # Invoices that are being added, not settled
        if not invoice.settle_date:
            return

        UpsertInvoices.upsert(
            single_invoice=invoice,
            local_pubkey=local_pubkey
        )

        invoice_data = MessageToDict(invoice)
        invoice_data['r_hash'] = r_hash = invoice.r_hash.hex()
        invoice_data['r_preimage'] = invoice.r_preimage.hex()

        capacity_request = InboundCapacityRequestQueries.get_by_invoice(r_hash)

        if capacity_request is None:
            log.info('Invoice not related to capacity request',
                     invoice_data=invoice_data)
            return

        if int(invoice_data['amt_paid_sat']) != capacity_request['total_fee']:
            log.error('Payment does not match liability',
                      invoice_data=invoice_data,
                      total_fee=capacity_request['total_fee'])
            return

        client_invoice_data = {
            'server_id': get_server_id('invoices'),
            'invoice_data': invoice_data,
            'session_id': capacity_request['session_id']
        }
        log.debug('sending paid invoice',
                  client_invoice_data=client_invoice_data)
        client_invoice_data_string = json.dumps(client_invoice_data)

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(MAIN_SERVER_WEBSOCKET_URL) as ws:
                await ws.send_str(client_invoice_data_string)
                await ws.close()

        chan_open_data = dict(
            server_id=get_server_id('invoices'),
            session_id=capacity_request['session_id'],
            type='open_channel',
            remote_pubkey=capacity_request['remote_pubkey'],
            local_funding_amount=capacity_request['capacity'],
            sat_per_byte=capacity_request['transaction_fee_rate']
        )
        log.debug('sending channel open instructions',
                  chan_open_data=chan_open_data)
        chan_open_data_string = json.dumps(chan_open_data)

        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(CHANNEL_OPENING_SERVER_WEBSOCKET_URL) as ws:
                await ws.send_str(chan_open_data_string)
                await ws.close()

    async def run(self):
        local_pubkey = self.rpc.get_info().identity_pubkey
        invoice_subscription = self.rpc.subscribe_invoices(
            add_index=UpsertInvoices.get_max_add_index()
        )
        for invoice in invoice_subscription:
            await self.handle_invoice(local_pubkey, invoice)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Invoice server'
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

    rpc = Client(
        grpc_host=args.host,
        grpc_port=args.port,
        macaroon_path=args.macaroon,
        tls_cert_path=args.tls
    )

    invoice_server = InvoiceServer(rpc=rpc)

    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, loop.stop)
    loop.create_task(invoice_server.run())
    loop.run_forever()
