import asyncio
import json

from google.protobuf.json_format import MessageToDict
import websockets
from sqlalchemy.orm.exc import NoResultFound

from lnd_grpc import lnd_grpc
from lnd_grpc.protos.rpc_pb2 import GetInfoResponse
from lnd_sql import session_scope
from lnd_sql.models import InboundCapacityRequest
from lnd_sql.scripts.upsert_invoices import UpsertInvoices
from website.logger import log
from websocket.constants import (
    CHANNEL_OPENING_SERVER_WEBSOCKET_URL,
    MAIN_SERVER_WEBSOCKET_URL
)
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
        invoice_subscription = self.rpc.subscribe_invoices(
            add_index=UpsertInvoices.get_max_add_index()
        )
        for invoice in invoice_subscription:
            # Invoices that are being added, not settled
            if not invoice.settle_date:
                continue

            UpsertInvoices.upsert(
                single_invoice=invoice,
                local_pubkey=self.info.identity_pubkey
            )

            invoice_data = MessageToDict(invoice)
            invoice_data['r_hash'] = invoice.r_hash.hex()
            invoice_data['r_preimage'] = invoice.r_preimage.hex()

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
                        invoice_data=invoice_data
                    )
                    continue

                if int(invoice_data['amt_paid_sat']) != inbound_capacity_request.total_fee:
                    log.error('Payment does not match liability',
                              invoice_data=invoice_data,
                              total_fee=inbound_capacity_request.total_fee)
                    continue

                async with websockets.connect(
                        MAIN_SERVER_WEBSOCKET_URL) as m_ws:
                    data = {
                        'server_id': get_server_id('invoices'),
                        'invoice_data': invoice_data,
                        'session_id': inbound_capacity_request.session_id
                    }
                    log.debug('sending paid invoice', data=data)
                    data_string = json.dumps(data)
                    await m_ws.send(data_string)

                async with websockets.connect(
                        CHANNEL_OPENING_SERVER_WEBSOCKET_URL) as co_ws:
                    data = dict(
                        server_id=get_server_id('invoices'),
                        session_id=inbound_capacity_request.session_id,
                        type='open_channel',
                        remote_pubkey=inbound_capacity_request.remote_pubkey,
                        local_funding_amount=inbound_capacity_request.capacity,
                        sat_per_byte=inbound_capacity_request.transaction_fee_rate
                    )
                    log.debug('sending channel open instructions', data=data)
                    data_string = json.dumps(data)
                    await co_ws.send(data_string)


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
