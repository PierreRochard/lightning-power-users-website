import json

from lnd_grpc.lnd_grpc import Client


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
