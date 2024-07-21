import json
from channels.generic.websocket import AsyncWebsocketConsumer

class GAProgressConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            "ga_progress",
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            "ga_progress",
            self.channel_name
        )

    async def receive(self, text_data):
        pass

    async def send_progress(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({
            'message': message
        }))
