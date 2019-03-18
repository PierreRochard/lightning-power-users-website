import asyncio
import json

from google.protobuf.json_format import MessageToDict
import websockets

from lnd_grpc import lnd_grpc
from lnd_sql.scripts.upsert_invoices import UpsertInvoices
from website.logger import log
from websocket.constants import (
    CHANNEL_OPENING_SERVER_WEBSOCKET_URL,
    MAIN_SERVER_WEBSOCKET_URL
)
from websocket.queries import InboundCapacityRequestQueries
from websocket.utilities import get_server_id


class InvoiceServer(object):
    def __init__(self,
                 lnd_dir: str = None,
                 lnd_network: str = 'mainnet',
                 lnd_grpc_host: str = 'localhost',
                 lnd_grpc_port: str = '10009',
                 tls_cert_path: str = None,
                 macaroon_path: str = None):
        self.rpc = lnd_grpc.Client(
            lnd_dir=lnd_dir,
            network=lnd_network,
            grpc_host=lnd_grpc_host,
            grpc_port=lnd_grpc_port,
            macaroon_path=macaroon_path,
            tls_cert_path=tls_cert_path
        )

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

        async with websockets.connect(MAIN_SERVER_WEBSOCKET_URL) as m_ws:
            await m_ws.send(client_invoice_data_string)

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

        async with websockets.connect(
                CHANNEL_OPENING_SERVER_WEBSOCKET_URL) as co_ws:
            await co_ws.send(chan_open_data_string)

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

    args = parser.parse_args()

    invoice_server = InvoiceServer(
        macaroon_path=args.macaroon,
        tls_cert_path=args.tls
    )

    asyncio.get_event_loop().run_until_complete(
        invoice_server.run()
    )
    asyncio.get_event_loop().run_forever()
