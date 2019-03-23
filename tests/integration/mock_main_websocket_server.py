import asyncio
import json

from aiohttp import web, WSMsgType
from flask_qrcode import QRcode

from website.logger import log
from websocket.logging_middleware import error_middleware


class MockMainWebsocket(web.View):

    async def get(self):
        websocket = web.WebSocketResponse()
        await websocket.prepare(self.request)

        async for msg in websocket:
            if msg.type == WSMsgType.text:
                if msg.data == 'close':
                    await websocket.close()
                    return

            elif msg.type == WSMsgType.error:
                log.debug(
                    'ws connection closed with exception %s' % websocket.exception())
                return

            data_from_client = json.loads(msg.data)

            action = data_from_client.get('action', None)
            if action == 'register':
                await websocket.send_json({'action': 'registered'})
            elif action == 'connect':
                await websocket.send_json({'action': 'error_message', 'error': 'error'})
                # await websocket.send_json({'action': 'connected', 'data': None})
            elif action == 'capacity_request':
                await websocket.send_json({'action': 'confirmed_capacity'})
            elif action == 'chain_fee':
                await websocket.send_json(
                    {
                        'action': 'payment_request',
                        'payment_request': 'mock_payment_request',
                        'qrcode': QRcode.qrcode('mock_qrcode', border=10),
                        'uri': 'mock_uri'
                    }
                )
                await asyncio.sleep(3)
                await websocket.send_json({'action': 'receive_payment'})
                await asyncio.sleep(3)
                await websocket.send_json(
                    {
                        'action': 'channel_open',
                        'url': f'https://blockstream.info',
                        'txid': 'fake_txid'
                    }
                )
            else:
                log.debug(
                    'Unknown action',
                    action=action,
                    data_from_client=data_from_client
                )


if __name__ == '__main__':
    app = web.Application(middlewares=[error_middleware])
    app.add_routes([web.get('/', MockMainWebsocket)])

    web.run_app(app, host='localhost', port=8765)
