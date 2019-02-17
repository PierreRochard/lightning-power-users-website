import json


class User(object):
    def __init__(self, ws):
        self.ws = ws

    async def send(self, message):
        message_string = json.dumps(message)
        await self.ws.send(message_string)


class Users(object):
    def __init__(self):
        self.users = {}

    async def register(self, tracker: str, websocket):
        self.users[tracker] = User(websocket)

    async def unregister(self, tracker: str):
        del self.users[tracker]

    async def notify_user(self, tracker: str, message):
        user = self.users.get(tracker, None)
        if user is None:
            return
        await user.send(json.dumps(message))
