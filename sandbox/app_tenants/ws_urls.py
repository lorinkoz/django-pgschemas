from django.urls import path

from sandbox.consumers import EchoConsumer

urlpatterns = [
    path("ws/tenant/", EchoConsumer.as_asgi(), name="tenant-ws"),
]
