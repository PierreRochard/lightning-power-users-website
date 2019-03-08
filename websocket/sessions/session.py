import json
from typing import List

from flask_qrcode import QRcode
from google.protobuf.json_format import MessageToDict
# noinspection PyProtectedMember
from grpc._channel import _Rendezvous
from structlog import get_logger
from websockets import WebSocketServerProtocol

from lnd_grpc.lnd_grpc import Client
from website.constants import EXPECTED_BYTES
from websocket.constants import PUBKEY_LENGTH
from websocket.queries.channel_queries import ChannelQueries


class Session(object):
    session_id: str
    rpc: Client
    ws: WebSocketServerProtocol

    def __init__(self,
                 session_id: str,
                 ws: WebSocketServerProtocol,
                 rpc: Client,
                 peer_pubkeys: List[str]):
        self.session_id = session_id
        self.ws = ws
        self.rpc = rpc
        self.peer_pubkeys = peer_pubkeys

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

    async def send_connected(self, remote_pubkey: str):
        data = ChannelQueries.get_peer_channel_totals(remote_pubkey)
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

    async def send_payreq(self, payment_request, qrcode):
        message = {
            'action': 'payment_request',
            'payment_request': payment_request,
            'qrcode': qrcode
        }
        await self.send(message=message)

    async def connect_to_peer(self, remote_pubkey_input: str):
        remote_pubkey = remote_pubkey_input.strip()
        if not remote_pubkey:
            self.log.debug(
                'Pressed connect button but no remote_pubkey found',
                remote_pubkey_input=remote_pubkey_input
            )
            await self.send_error_message(
                'Please enter your PubKey'
            )
            return

        if '@' in remote_pubkey:
            # noinspection PyBroadException
            try:
                remote_pubkey, remote_host = remote_pubkey.split('@')
                self.log.debug(
                    'Parsed host',
                    remote_pubkey=remote_pubkey,
                    remote_host=remote_host
                )
            except:
                self.log.error(
                    'Invalid PubKey format',
                    remote_pubkey=remote_pubkey,
                    exc_info=True
                )
                await self.send_error_message(
                    error='Invalid PubKey format'
                )
                return
        else:
            remote_host = None

        if len(remote_pubkey) != PUBKEY_LENGTH:
            self.log.error('Invalid PubKey length', pubkey=remote_pubkey)
            await self.send_error_message(
                f'Invalid PubKey length, expected {PUBKEY_LENGTH} characters'
            )
            return

        # Connect to peer
        if remote_host is None:
            try:
                assert [p for p in self.peer_pubkeys if p == remote_pubkey][0]
                self.log.debug(
                    'Already connected to peer',
                    remote_pubkey=remote_pubkey
                )
                await self.send_connected(
                    remote_pubkey=remote_pubkey
                )
                return
            except IndexError:
                self.log.debug(
                    'Unknown PubKey, please provide pubkey@host:port',
                    pubkey=remote_pubkey,
                    exc_info=True
                )
                await self.send_error_message(
                    'Unknown PubKey, please provide pubkey@host:port'
                )
                return

        try:
            self.rpc.connect('@'.join([remote_pubkey, remote_host]))
            self.log.debug(
                'Connected to peer',
                remote_pubkey=remote_pubkey
            )
            await self.send_connected(
                remote_pubkey=remote_pubkey
            )
            return

        except _Rendezvous as e:
            details = e.details()
            if 'already connected to peer' in details:
                self.log.debug(
                    'Already connected to peer',
                    remote_pubkey=remote_pubkey
                )
                await self.send_connected(
                    remote_pubkey=remote_pubkey
                )
                return
            else:
                self.log.error(
                    'connect_peer',
                    remote_pubkey=remote_pubkey,
                    remote_host=remote_host,
                    details=details,
                    exc_info=True
                )
                await self.send_error_message(
                    f'Error: {details}'
                )
                return

    async def confirm_capacity(self, form_data):
        self.log.debug(
            'confirm_capacity',
            session_id=self.session_id,
            form_data=form_data
        )
        await self.send_confirmed_capacity()

    async def chain_fee(self, data: dict):
        self.log.debug(
            'chain_fee',
            session_id=self.session_id,
            data=data
        )

        selected_capacity = data.get('selected_capacity', None)
        selected_capacity_rate = data.get('selected_capacity_rate')
        selected_chain_fee = data.get('selected_chain_fee')

        capacity_fee = int(selected_capacity * selected_capacity_rate)

        transaction_fee = selected_chain_fee * EXPECTED_BYTES
        total_fee = capacity_fee + transaction_fee

        memo = 'Lightning Power Users capacity request: '
        if selected_capacity == 0:
            memo += 'reciprocate'
        else:
            memo += f'{selected_capacity} @ {selected_capacity_rate}'

        invoice = self.rpc.add_invoice(
            value=int(total_fee),
            memo=memo
        )
        invoice = MessageToDict(invoice)
        payment_request = invoice['payment_request']
        uri = ':'.join(['lightning', payment_request])
        qrcode = QRcode.qrcode(uri, border=10)

        await self.send_payreq(payment_request, qrcode)
