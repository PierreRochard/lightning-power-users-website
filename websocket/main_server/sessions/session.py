import json
from decimal import Decimal

from flask_qrcode import QRcode
# noinspection PyProtectedMember
from grpc._channel import _Rendezvous
from sqlalchemy.orm.exc import NoResultFound
from structlog import get_logger
from websockets import WebSocketServerProtocol

from lnd_grpc.lnd_grpc import Client
from lnd_sql import session_scope
from lnd_sql.models import ActivePeers
from lnd_sql.models.contrib.inbound_capacity_request import \
    InboundCapacityRequest
from lnd_sql.scripts.upsert_invoices import UpsertInvoices
from website.constants import EXPECTED_BYTES, CAPACITY_FEE_RATES
from websocket.constants import PUBKEY_LENGTH
from websocket.queries import InboundCapacityRequestQueries
from websocket.queries.channel_queries import ChannelQueries


class Session(object):
    reciprocate_capacity: int
    remote_host: str
    remote_pubkey: str
    rpc: Client
    session_id: str
    ws: WebSocketServerProtocol

    def __init__(self,
                 session_id: str,
                 local_pubkey: str,
                 ws: WebSocketServerProtocol,
                 rpc: Client):
        self.session_id = session_id
        self.local_pubkey = local_pubkey
        self.ws = ws
        self.rpc = rpc

        self.remote_host = None
        self.remote_pubkey = None

        self.reciprocate_capacity = None

        logger = get_logger()
        self.log = logger.bind(session_id=session_id)

    async def send(self, message):
        message_string = json.dumps(message)
        await self.ws.send(message_string)

    async def send_registered(self):
        message = {
            'action': 'registered'
        }
        await self.send(message=message)

    async def send_connected(self):
        data = ChannelQueries.get_peer_channel_totals(self.remote_pubkey)
        self.log.debug('get_peer_channel_totals', data=data)

        if data is not None:
            if data['count'] > 1:
                await self.send_error_message(
                    error=f'{data["count"]} channels already open between us, '
                    f'please close {data["count"]-1}'
                )
                return

            if data['balance'] is not None and data['balance'] > 0.7:
                await self.send_error_message(
                    error='Our existing channel already has inbound capacity '
                          'in your favor, please close it to request more '
                          'capacity'
                )
                return

            self.reciprocate_capacity = int(data['capacity'])

        InboundCapacityRequestQueries.insert(
            session_id=self.session_id,
            remote_pubkey=self.remote_pubkey,
            remote_host=self.remote_host
        )

        message = {
            'action': 'connected',
            'data': data
        }
        await self.send(message=message)

    async def send_error_message(self, error: str):
        message = {
            'action': 'error_message',
            'error': error
        }
        await self.send(message=message)

    async def send_confirmed_capacity(self):
        message = {
            'action': 'confirmed_capacity',
        }
        await self.send(message=message)

    async def send_payreq(self, payment_request, uri, qrcode):
        self.log.debug('send_payreq')
        message = {
            'action': 'payment_request',
            'payment_request': payment_request,
            'qrcode': qrcode,
            'uri': uri
        }
        await self.send(message=message)

    async def parse_remote_pubkey(self, remote_pubkey_input: str):
        self.remote_pubkey = remote_pubkey_input.strip()
        if not self.remote_pubkey:
            self.log.debug(
                'Pressed connect button but no remote_pubkey found',
                remote_pubkey_input=remote_pubkey_input
            )
            await self.send_error_message(
                'Please enter your PubKey'
            )
            self.remote_pubkey = None
            return

        if '@' in self.remote_pubkey:
            # noinspection PyBroadException
            try:
                self.remote_pubkey, self.remote_host = self.remote_pubkey.split('@')
                self.log.debug(
                    'Parsed host',
                    remote_pubkey=self.remote_pubkey,
                    remote_host=self.remote_host
                )
            except:
                self.log.error(
                    'Invalid PubKey format',
                    remote_pubkey=self.remote_pubkey,
                    exc_info=True
                )
                await self.send_error_message(
                    error='Invalid PubKey format'
                )
                self.remote_pubkey = None
                return
        else:
            self.remote_host = None

        if len(self.remote_pubkey) != PUBKEY_LENGTH:
            self.log.error('Invalid PubKey length', pubkey=self.remote_pubkey)
            await self.send_error_message(
                f'Invalid PubKey length, expected {PUBKEY_LENGTH} characters'
            )
            self.remote_pubkey = None
            return

    async def connect_to_peer(self, remote_pubkey_input: str):
        self.log.debug(
            'connect_to_peer',
            remote_pubkey_input=remote_pubkey_input
        )
        await self.parse_remote_pubkey(remote_pubkey_input)
        if not self.remote_pubkey:
            return

        # Connect to peer
        if self.remote_host is None:
            try:
                with session_scope() as session:
                    peer = (
                        session.query(ActivePeers).filter(
                            ActivePeers.remote_pubkey == self.remote_pubkey)
                        .one()
                    )
                self.log.debug(
                    'Already connected to peer',
                    remote_pubkey=self.remote_pubkey
                )
                await self.send_connected()
                return
            except NoResultFound:
                self.log.debug(
                    'Unknown PubKey, please provide pubkey@host:port',
                    pubkey=self.remote_pubkey,
                    exc_info=True
                )
                await self.send_error_message(
                    'Unknown PubKey, please provide pubkey@host:port'
                )
                return

        try:
            address = '@'.join([self.remote_pubkey, self.remote_host])
            self.rpc.connect(address=address, timeout=3)
            self.log.debug(
                'Connected to peer',
                remote_pubkey=self.remote_pubkey
            )
            await self.send_connected()
            return

        except _Rendezvous as e:
            details = e.details()
            if 'already connected to peer' in details:
                self.log.debug(
                    'Already connected to peer',
                    remote_pubkey=self.remote_pubkey
                )
                await self.send_connected()
                return
            else:
                self.log.error(
                    'connect_peer',
                    remote_pubkey=self.remote_pubkey,
                    remote_host=self.remote_host,
                    details=details,
                    exc_info=True
                )
                await self.send_error_message(
                    f'Error: {details}, please connect to our node 0331f80652fb840239df8dc99205792bba2e559a05469915804c08420230e23c7c@lightningpowerusers.com:9735'
                )
                return

    async def confirm_capacity(self, form_data):
        self.log.debug(
            'confirm_capacity',
            session_id=self.session_id,
            form_data=form_data
        )
        with session_scope() as session:
            request: InboundCapacityRequest = (
                session.query(InboundCapacityRequest)
                .filter(InboundCapacityRequest.session_id == self.session_id)
                .order_by(InboundCapacityRequest.updated_at.desc())
                .first()
            )
            request.capacity = int([f['value'] for f in form_data
                                    if f['name'] == 'capacity'][0])
            try:
                request.capacity_fee_rate = Decimal([f['value'] for f in form_data
                                                     if f['name'] == 'capacity_fee_rate'][0])
                assert request.capacity_fee_rate in [c[0] for c in CAPACITY_FEE_RATES]
            except IndexError:
                request.capacity_fee_rate = 0
                assert request.capacity == self.reciprocate_capacity
            request.capacity_fee = request.capacity * request.capacity_fee_rate
        await self.send_confirmed_capacity()

    async def chain_fee(self, form_data):
        self.log.debug(
            'chain_fee',
            session_id=self.session_id,
            form_data=form_data
        )
        with session_scope() as session:
            inbound_capacity_request: InboundCapacityRequest = (
                session.query(InboundCapacityRequest)
                    .filter(InboundCapacityRequest.session_id == self.session_id)
                    .order_by(InboundCapacityRequest.updated_at.desc())
                    .first()
            )

            inbound_capacity_request.transaction_fee_rate = int([f['value'] for f in form_data
                                    if f['name'] == 'transaction_fee_rate'][0])
            assert inbound_capacity_request.transaction_fee_rate > 0
            inbound_capacity_request.expected_bytes = EXPECTED_BYTES
            inbound_capacity_request.transaction_fee = inbound_capacity_request.transaction_fee_rate * EXPECTED_BYTES
            inbound_capacity_request.total_fee = inbound_capacity_request.capacity_fee + inbound_capacity_request.transaction_fee

            memo = 'Lightning Power Users capacity request: '
            if inbound_capacity_request.capacity_fee_rate:
                memo += f'{inbound_capacity_request.capacity} ' \
                    f'@ {inbound_capacity_request.capacity_fee_rate}'
            else:
                memo += f'reciprocate {inbound_capacity_request.capacity}'

            add_invoice_response = self.rpc.add_invoice(
                value=int(inbound_capacity_request.total_fee),
                memo=memo
            )
            invoice = self.rpc.lookup_invoice(r_hash=add_invoice_response.r_hash)
            UpsertInvoices.upsert(
                single_invoice=invoice,
                local_pubkey=self.local_pubkey
            )

            inbound_capacity_request.payment_request = invoice.payment_request
            inbound_capacity_request.invoice_r_hash = invoice.r_hash.hex()
            uri = ':'.join(['lightning',
                            inbound_capacity_request.payment_request])
            qrcode = QRcode.qrcode(uri, border=10)
            payment_request = inbound_capacity_request.payment_request

        await self.send_payreq(
            payment_request=payment_request,
            uri=uri,
            qrcode=qrcode
        )

    async def receive_payment(self):
        message = {
            'action': 'receive_payment'
        }
        await self.send(message=message)

    async def channel_open(self, data: dict):
        if data.get('error', None):
            await self.send_error_message(data['error'])
            return
        txid = data['open_channel_update']['chan_pending']['txid']
        message = {
            'action': 'channel_open',
            'url': f'https://blockstream.info/tx/{txid}',
            'txid': txid
        }
        await self.send(message=message)
