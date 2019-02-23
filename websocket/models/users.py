import json

from google.protobuf.json_format import MessageToDict
# noinspection PyProtectedMember
from grpc._channel import _Rendezvous
from structlog import get_logger

from lnd_grpc.lnd_grpc import Client
from website.logger import log
from websocket.constants import PUBKEY_LENGTH


class User(object):
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


class Users(object):
    rpc: Client

    def __init__(self, rpc):
        self.rpc = rpc
        self.connections = {}

    async def send(self, user_id: str, message):
        user = self.connections.get(user_id, None)
        if user is None:
            return
        await user.send(message)

    async def handle_user_message(self,
                                  websocket,
                                  user_id,
                                  data_from_client):
        action = data_from_client.get('action', None)
        if action == 'register':
            await self.register(
                user_id=user_id,
                websocket=websocket
            )
        elif action == 'connect':
            log.debug('connect', data_from_client=data_from_client)
            form_data = data_from_client.get('form_data', None)
            form_data_pubkey = [f for f in form_data if f['name'] == 'pubkey'][0]
            if not len(form_data_pubkey):
                log.debug(
                    'Connect did not include valid form data',
                    data_from_client=data_from_client
                )
                return
            pubkey = form_data_pubkey.get('value', '').strip()
            await self.connect_to_peer(user_id, pubkey)
        elif action == 'capacity_request':
            form_data = data_from_client.get('form_data', None)
            await self.confirm_capacity(user_id, form_data)
        elif action is not None:
            log.debug('Unknown action',
                      action=action,
                      data_from_client=data_from_client)

    async def register(self, user_id: str, websocket):
        log.info(
            'Registering user_id',
            user_id=user_id
        )
        self.connections[user_id] = User(websocket, self.rpc)
        await self.connections[user_id].send_registered()

    async def unregister(self, user_id: str):
        del self.connections[user_id]

    async def connect_to_peer(self, user_id: str, remote_pubkey_input: str):
        logger = get_logger()
        log_user = logger.bind(user_id=user_id)
        user_websocket: User = self.connections[user_id]
        remote_pubkey = remote_pubkey_input.strip()
        if not remote_pubkey:
            log_user.debug(
                'Pressed connect button but no remote_pubkey found',
                remote_pubkey_input=remote_pubkey_input
            )
            await user_websocket.send_connect_error('Please enter your PubKey')
            return

        full_remote_pubkey = remote_pubkey
        if '@' in remote_pubkey:
            # noinspection PyBroadException
            try:
                remote_pubkey, remote_host = remote_pubkey.split('@')
                log_user.debug('Parsed host', remote_host=remote_host)
            except:
                log_user.error('Invalid PubKey format',
                               remote_pubkey=remote_pubkey,
                               exc_info=True)
                await user_websocket.send_connect_error('Invalid PubKey format')
                return
        else:
            remote_host = None

        if len(remote_pubkey) != PUBKEY_LENGTH:
            log_user.error('Invalid PubKey length', pubkey=remote_pubkey)
            await user_websocket.send_connect_error(
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
                log_user.error(
                    'Error with list_peers rpc',
                    exc_info=True
                )
                await user_websocket.send_connect_error('Error: please refresh and try again')
                return

            try:
                peer = [p for p in peers if p.pub_key == remote_pubkey][0]
                log_user.debug('Already connected to peer',
                               remote_pubkey=remote_pubkey,
                               peer=MessageToDict(peer))
                await user_websocket.send_connected(remote_pubkey=remote_pubkey)
                return
            except IndexError:
                log_user.debug(
                    'Unknown PubKey, please provide pubkey@host:port',
                    pubkey=remote_pubkey,
                    exc_info=True)
                await user_websocket.send_connect_error(
                    'Unknown PubKey, please provide pubkey@host:port'
                )
                return
        else:
            try:
                self.rpc.connect(address=full_remote_pubkey)
                log_user.debug('Connected to peer',
                               remote_pubkey=remote_pubkey)
                await user_websocket.send_connected(remote_pubkey=remote_pubkey)
                return

            except _Rendezvous as e:
                details = e.details()
                if 'already connected to peer' in details:
                    log_user.debug('Already connected to peer',
                                   remote_pubkey=remote_pubkey)
                    await user_websocket.send_connected(remote_pubkey=remote_pubkey)
                    return
                else:
                    log_user.error('connect_peer',
                                   remote_pubkey=remote_pubkey,
                                   remote_host=remote_host,
                                   details=details,
                                   exc_info=True)
                    await user_websocket.send_connect_error(f'Error: {details}')
                    return

    async def confirm_capacity(self, user_id, form_data):
        log.debug('confirm_capacity', user_id=user_id, form_data=form_data)

        user_websocket: User = self.connections[user_id]
        await user_websocket.send_confirmed_capacity()
