import json

from channels.generic.websocket import AsyncWebsocketConsumer


class EchoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data["message"]

        schema_name = self.scope["tenant"].schema_name
        await self.send(text_data=json.dumps({"message": f"{schema_name}: {message}"}))
