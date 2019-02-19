import json

# noinspection PyProtectedMember
from google.protobuf.json_format import MessageToDict
from grpc._channel import _Rendezvous
from structlog import get_logger

from lnd_grpc.lnd_grpc import Client
from website.logger import log
from websocket.constants import PUBKEY_LENGTH


class User(object):
    def __init__(self, ws):
        self.ws = ws

    async def send(self, message):
        message_string = json.dumps(message)
        await self.ws.send(message_string)

    async def send_connected(self, remote_pubkey: str):
        message = {
            'action': 'connected'
        }
        await self.send(message=message)
        pass

    async def send_error(self, error: str):
        message = {
            'error': error,
            'category': 'danger'
        }
        await self.send(message=message)


class Users(object):
    rpc: Client

    def __init__(self, rpc):
        self.rpc = rpc
        self.connections = {}

    async def register(self, user_id: str, websocket):
        if user_id not in self.connections:
            log.info(
                'Registering user_id',
                user_id=user_id
            )
            self.connections[user_id] = User(websocket)

    async def unregister(self, user_id: str):
        del self.connections[user_id]

    async def send(self, user_id: str, message):
        user = self.connections.get(user_id, None)
        if user is None:
            return
        await user.send(message)

    async def process_pubkey(self, user_id: str, remote_pubkey_input: str):
        logger = get_logger()
        log_user = logger.bind(user_id=user_id)
        user_websocket: User = self.connections[user_id]
        remote_pubkey = remote_pubkey_input.strip()
        if not remote_pubkey:
            log_user.debug(
                'Pressed connect button but no remote_pubkey found',
                remote_pubkey_input=remote_pubkey_input
            )
            await user_websocket.send_error('Please enter your PubKey')
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
                await user_websocket.send_error('Invalid PubKey format')
                return
        else:
            remote_host = None

        if len(remote_pubkey) != PUBKEY_LENGTH:
            log_user.error('Invalid PubKey length', pubkey=remote_pubkey)
            await user_websocket.send_error(
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
                await user_websocket.send_error('Error: please refresh and try again')
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
                await user_websocket.send_error(
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
                    await user_websocket.send_error(f'Error: {details}')
                    return
