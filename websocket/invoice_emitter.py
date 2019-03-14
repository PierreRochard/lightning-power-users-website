import asyncio
import json

from google.protobuf.json_format import MessageToDict
import websockets

from lnd_grpc import lnd_grpc
from lnd_grpc.protos.rpc_pb2 import GetInfoResponse
from lnd_sql.scripts.upsert_invoices import UpsertInvoices
from website.logger import log
from websocket.constants import MAIN_SERVER_WEBSOCKET_URL
from websocket.utilities import get_server_id


class InvoiceEmitter(object):
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
        self.info: GetInfoResponse = self.rpc.get_info()

        asyncio.get_event_loop().run_until_complete(
            self.send_to_server()
        )
        asyncio.get_event_loop().run_forever()

    async def send_to_server(self):
        async with websockets.connect(MAIN_SERVER_WEBSOCKET_URL) as websocket:
            invoice_subscription = self.rpc.subscribe_invoices(settle_index=1)
            for invoice in invoice_subscription:
                UpsertInvoices.upsert(
                    single_invoice=invoice,
                    local_pubkey=self.info.identity_pubkey
                )
                invoice_data = MessageToDict(invoice)
                invoice_data['r_hash'] = invoice.r_hash.hex()
                invoice_data['r_preimage'] = invoice.r_preimage.hex()
                data = {
                    'server_id': get_server_id('invoices'),
                    'invoice_data': invoice_data
                }
                data_string = json.dumps(data)
                log.debug('sending websocket message', data=data)
                await websocket.send(data_string)


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='LND Node Operator Tools'
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

    args = parser.parse_args()

    InvoiceEmitter(
        macaroon_path=args.macaroon,
        tls_cert_path=args.tls
    )
