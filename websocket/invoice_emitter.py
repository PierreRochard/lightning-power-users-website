import asyncio
import json

import websockets
from google.protobuf.json_format import MessageToDict

from lnd_grpc import lnd_grpc
from website.logger import log
from websocket.constants import DEFAULT_WEBSOCKET_URL
from websocket.utilities import get_server_id


class InvoiceEmitter(object):
    def __init__(self,
                 websocket_url: str = DEFAULT_WEBSOCKET_URL,
                 lnd_dir: str = None,
                 lnd_network: str = 'mainnet',
                 lnd_grpc_host: str = 'localhost',
                 lnd_grpc_port: str = '10011'):
        self.rpc = lnd_grpc.Client(
            lnd_dir=lnd_dir,
            network=lnd_network,
            grpc_host=lnd_grpc_host,
            grpc_port=lnd_grpc_port,
        )

        asyncio.get_event_loop().run_until_complete(self.send_to_server(websocket_url))
        asyncio.get_event_loop().run_forever()

    async def send_to_server(self, websocket_url: str):
        async with websockets.connect(websocket_url) as websocket:
            invoice_subscription = self.rpc.subscribe_invoices(settle_index=1)
            for invoice in invoice_subscription:
                data = {
                    'server_id': get_server_id('invoices'),
                    'invoice_data': MessageToDict(invoice)
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
        '--verbose',
        '-v',
        action='store_true',
        help='Display additional information for debugging'
    )

    parser.add_argument(
        '--websocket_url',
        '-w',
        type=str,
        help='The server websocket url',
        default=DEFAULT_WEBSOCKET_URL
    )

    args = parser.parse_args()

    InvoiceEmitter(websocket_url=args.websocket_url)
