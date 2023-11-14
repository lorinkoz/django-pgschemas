from channels.generic.websocket import JsonWebsocketConsumer
from django.urls import path

urlpatterns = [
    path("", JsonWebsocketConsumer, name="main-ws"),
]
