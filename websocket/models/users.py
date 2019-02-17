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

    async def register(self, user_id: str, websocket):
        self.users[user_id] = User(websocket)

    async def unregister(self, user_id: str):
        del self.users[user_id]

    async def send(self, user_id: str, message):
        user = self.users.get(user_id, None)
        if user is None:
            return
        await user.send(json.dumps(message))
