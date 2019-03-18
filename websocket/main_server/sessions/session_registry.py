from typing import Dict

from websockets import WebSocketServerProtocol

from lnd_grpc.lnd_grpc import Client
from lnd_grpc.protos.rpc_pb2 import GetInfoResponse
from website.logger import log
from websocket.main_server.sessions.session import Session


class SessionRegistry(object):
    info: GetInfoResponse
    sessions: Dict[str, Session]
    rpc: Client

    def __init__(self, rpc):
        self.rpc = rpc
        self.info = self.rpc.get_info()
        self.sessions = {}

    async def handle_session_message(
            self,
            session_id: str,
            data_from_client: dict,
            session_websocket: WebSocketServerProtocol = None
    ):
        action = data_from_client.get('action', None)
        if action is None:
            return

        if action == 'register':
            await self.register(
                session_id=session_id,
                session_websocket=session_websocket
            )
        elif action == 'connect':
            log.debug('connect', data_from_client=data_from_client)
            form_data = data_from_client.get('form_data', None)
            form_data_pubkey = [f for f in form_data
                                if f['name'] == 'pubkey'][0]
            if not len(form_data_pubkey):
                log.debug(
                    'Connect did not include valid form data',
                    data_from_client=data_from_client
                )
                return
            pubkey = form_data_pubkey.get('value', '').strip()
            await self.sessions[session_id].connect_to_peer(pubkey)
        elif action == 'capacity_request':
            form_data = data_from_client.get('form_data', None)
            await self.sessions[session_id].confirm_capacity(form_data)
        elif action == 'chain_fee':
            form_data = data_from_client.get('form_data', None)
            await self.sessions[session_id].chain_fee(form_data)
        elif action == 'receive_payment':
            await self.sessions[session_id].receive_payment()
        elif action == 'channel_open':
            await self.sessions[session_id].channel_open(data_from_client)
        else:
            log.debug(
                'Unknown action',
                action=action,
                data_from_client=data_from_client
            )

    async def register(self, session_id: str,
                       session_websocket: WebSocketServerProtocol):
        log.info(
            'Registering session_id',
            session_id=session_id
        )
        self.sessions[session_id] = Session(
            session_id=session_id,
            local_pubkey=self.info.identity_pubkey,
            ws=session_websocket,
            rpc=self.rpc,
        )
        await self.sessions[session_id].send_registered()

    async def unregister(self, session_id: str):
        del self.sessions[session_id]
