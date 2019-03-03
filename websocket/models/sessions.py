import json

from flask_qrcode import QRcode
from google.protobuf.json_format import MessageToDict
# noinspection PyProtectedMember
from grpc._channel import _Rendezvous
from structlog import get_logger

from lnd_grpc.lnd_grpc import Client
from website.constants import EXPECTED_BYTES
from website.logger import log
from websocket.constants import PUBKEY_LENGTH


class Session(object):
    def __init__(self, ws, rpc):
        self.ws = ws
        self.rpc: Client = rpc

    async def send(self, message):
        message_string = json.dumps(message)
        await self.ws.send(message_string)

    async def send_connected(self, remote_pubkey: str):
        channels = self.rpc.list_channels(public_only=True)
        channels = [c for c in channels
                    if c.remote_pubkey == remote_pubkey]
        if not channels:
            data = None
        else:
            data = {
                'channel_count': len(channels)
            }
        message = {
            'action': 'connected',
            'data': data
        }
        await self.send(message=message)

    async def send_registered(self):
        message = {
            'action': 'registered'
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


class Sessions(object):
    rpc: Client

    def __init__(self, rpc):
        self.rpc = rpc
        self.connections = {}

    async def send(self, session_id: str, message):
        session = self.connections.get(session_id, None)
        if session is None:
            return
        await session.send(message)

    async def handle_session_message(self,
                                     websocket,
                                     session_id,
                                     data_from_client):
        action = data_from_client.get('action', None)
        if action == 'register':
            await self.register(
                session_id=session_id,
                websocket=websocket
            )
        elif action == 'connect':
            log.debug('connect', data_from_client=data_from_client)
            form_data = data_from_client.get('form_data', None)
            form_data_pubkey = [f for f in form_data if f['name'] == 'pubkey'][
                0]
            if not len(form_data_pubkey):
                log.debug(
                    'Connect did not include valid form data',
                    data_from_client=data_from_client
                )
                return
            pubkey = form_data_pubkey.get('value', '').strip()
            await self.connect_to_peer(session_id, pubkey)
        elif action == 'capacity_request':
            form_data = data_from_client.get('form_data', None)
            await self.confirm_capacity(session_id, form_data)
        elif action == 'chain_fee':
            await self.chain_fee(session_id, data_from_client)
        elif action is not None:
            log.debug('Unknown action',
                      action=action,
                      data_from_client=data_from_client)

    async def register(self, session_id: str, websocket):
        log.info(
            'Registering session_id',
            session_id=session_id
        )
        self.connections[session_id] = Session(websocket, self.rpc)
        await self.connections[session_id].send_registered()

    async def unregister(self, session_id: str):
        del self.connections[session_id]

    async def connect_to_peer(self, session_id: str, remote_pubkey_input: str):
        logger = get_logger()
        log_session = logger.bind(session_id=session_id)
        session_websocket: Session = self.connections[session_id]
        remote_pubkey = remote_pubkey_input.strip()
        if not remote_pubkey:
            log_session.debug(
                'Pressed connect button but no remote_pubkey found',
                remote_pubkey_input=remote_pubkey_input
            )
            await session_websocket.send_error_message(
                'Please enter your PubKey')
            return

        full_remote_pubkey = remote_pubkey
        if '@' in remote_pubkey:
            # noinspection PyBroadException
            try:
                remote_pubkey, remote_host = remote_pubkey.split('@')
                log_session.debug('Parsed host', remote_host=remote_host)
            except:
                log_session.error('Invalid PubKey format',
                                  remote_pubkey=remote_pubkey,
                                  exc_info=True)
                await session_websocket.send_error_message(
                    'Invalid PubKey format')
                return
        else:
            remote_host = None

        if len(remote_pubkey) != PUBKEY_LENGTH:
            log_session.error('Invalid PubKey length', pubkey=remote_pubkey)
            await session_websocket.send_error_message(
                f'Invalid PubKey length, expected {PUBKEY_LENGTH} characters'
            )
            return

        # Connect to peer
        if remote_host is None:
            # noinspection PyBroadException
            try:
                # Check if we're already connected
                peers = self.rpc.list_peers()
            except:
                log_session.error(
                    'Error with list_peers rpc',
                    exc_info=True
                )
                await session_websocket.send_error_message(
                    'Error: please refresh and try again')
                return

            try:
                peer = [p for p in peers if p.pub_key == remote_pubkey][0]
                log_session.debug('Already connected to peer',
                                  remote_pubkey=remote_pubkey,
                                  peer=MessageToDict(peer))
                await session_websocket.send_connected(
                    remote_pubkey=remote_pubkey)
                return
            except IndexError:
                log_session.debug(
                    'Unknown PubKey, please provide pubkey@host:port',
                    pubkey=remote_pubkey,
                    exc_info=True)
                await session_websocket.send_error_message(
                    'Unknown PubKey, please provide pubkey@host:port'
                )
                return
        else:
            try:
                self.rpc.connect(address=full_remote_pubkey)
                log_session.debug('Connected to peer',
                                  remote_pubkey=remote_pubkey)
                await session_websocket.send_connected(
                    remote_pubkey=remote_pubkey)
                return

            except _Rendezvous as e:
                details = e.details()
                if 'already connected to peer' in details:
                    log_session.debug('Already connected to peer',
                                      remote_pubkey=remote_pubkey)
                    await session_websocket.send_connected(
                        remote_pubkey=remote_pubkey)
                    return
                else:
                    log_session.error('connect_peer',
                                      remote_pubkey=remote_pubkey,
                                      remote_host=remote_host,
                                      details=details,
                                      exc_info=True)
                    await session_websocket.send_error_message(
                        f'Error: {details}')
                    return

    async def confirm_capacity(self, session_id, form_data):
        log.debug('confirm_capacity', session_id=session_id,
                  form_data=form_data)

        session_websocket: Session = self.connections[session_id]
        await session_websocket.send_confirmed_capacity()

    async def chain_fee(self, session_id, data):
        log.debug('chain_fee', session_id=session_id, data=data)

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

        session_websocket: Session = self.connections[session_id]
        await session_websocket.send_payreq(payment_request, qrcode)
