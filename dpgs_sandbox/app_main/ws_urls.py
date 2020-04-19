from django.urls import path

from channels.generic.websocket import JsonWebsocketConsumer


urlpatterns = [
    path("", JsonWebsocketConsumer, name="main-ws"),
]
