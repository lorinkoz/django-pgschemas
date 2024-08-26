from django.urls import path

from sandbox.consumers import EchoConsumer

urlpatterns = [
    path("ws/main/", EchoConsumer.as_asgi(), name="main-ws"),
]
