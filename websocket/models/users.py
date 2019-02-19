import json

# noinspection PyProtectedMember
from google.protobuf.json_format import MessageToDict
from grpc._channel import _Rendezvous

from lnd_grpc.lnd_grpc import Client
from website.logger import log
from websocket.constants import PUBKEY_LENGTH


class User(object):
    def __init__(self, ws):
        self.ws = ws

    async def send(self, message):
        message_string = json.dumps(message)
        await self.ws.send(message_string)


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
        await user.send(json.dumps(message))

    async def process_pubkey(self, user_id: str, remote_pubkey_input: str):
        remote_pubkey = remote_pubkey_input.strip()
        if not remote_pubkey:
            log.debug(
                'Pressed connect button but no remote_pubkey found',
                user_id=user_id,
                remote_pubkey_input=remote_pubkey_input
            )
            message = {
                'error': 'Please enter your PubKey',
                'category': 'danger'
            }
            await self.send(user_id=user_id, message=message)
            return

        full_remote_pubkey = remote_pubkey
        if '@' in remote_pubkey:
            try:
                remote_pubkey, remote_host = remote_pubkey.split('@')
                log.debug('Parsed host', remote_host=remote_host)
            except:
                log.error('Invalid PubKey format', remote_pubkey=remote_pubkey,
                          exc_info=True)
                message = {
                    'error': 'Invalid PubKey format',
                    'category': 'danger'
                }
                await self.send(user_id=user_id, message=message)
                return
        else:
            remote_host = None

        if len(remote_pubkey) != PUBKEY_LENGTH:
            log.error('Invalid PubKey length', pubkey=remote_pubkey)
            message = {
                'error': f'Invalid PubKey length, expected {PUBKEY_LENGTH} characters',
                'category': 'danger'
            }
            await self.send(user_id=user_id, message=message)
            return

        # Connect to peer
        if remote_host is None:
            try:
                peers = self.rpc.list_peers()
            except:
                log.error(
                    'Error with list_peers rpc',
                    exc_info=True
                )
                message = {
                    'error': 'Error: please refresh and try again',
                    'category': 'danger'
                }
                await self.send(user_id=user_id, message=message)
                return

            try:
                peer = [p for p in peers if p.pub_key == remote_pubkey][0]
                log.debug('Already connected to peer',
                          remote_pubkey=remote_pubkey,
                          peer=MessageToDict(peer))
                message = {
                    'action': 'connected'
                }
                await self.send(user_id=user_id, message=message)
                return
            except IndexError:
                message = {
                    'error': 'Unknown PubKey, please provide pubkey@host:port',
                    'category': 'danger'
                }
                log.debug('Unknown PubKey, please provide pubkey@host:port',
                          pubkey=remote_pubkey,
                          exc_info=True)
                await self.send(user_id=user_id, message=message)
                return
        else:
            try:
                self.rpc.connect(address=full_remote_pubkey)
                log.debug('Connected to peer',
                          remote_pubkey=remote_pubkey)
                message = {
                    'action': 'connected'
                }
                await self.send(user_id=user_id, message=message)
                return

            except _Rendezvous as e:
                details = e.details()
                if 'already connected to peer' in details:
                    log.debug('Connected to peer',
                              remote_pubkey=remote_pubkey)
                    message = {
                        'action': 'connected'
                    }
                    await self.send(user_id=user_id, message=message)
                    return
                else:
                    message = {
                        'error': f'Error: {details}',
                        'category': 'danger'
                    }
                    log.error('connect_peer', pubkey=remote_pubkey,
                              remote_host=remote_host,
                              details=details,
                              exc_info=True)
                    await self.send(user_id=user_id, message=message)
                    return
