import pytest
from channels.testing import WebsocketCommunicator

from sandbox.routing import application


@pytest.mark.asyncio
async def test_on_main():
    communicator = WebsocketCommunicator(
        application,
        "/ws/main/",
        headers=[(b"host", b"localhost")],
    )
    connected, subprotocol = await communicator.connect()

    assert connected

    # Send a message
    await communicator.send_json_to({"message": "hello"})

    # Receive the message
    response = await communicator.receive_json_from()
    assert response["message"] == "www: hello"

    # Close the connection
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_on_tenant_subdomain(tenant1, DomainModel):
    if DomainModel is None:
        pytest.skip("Domain model is not in use")

    await DomainModel.objects.acreate(tenant=tenant1, domain="tenant1.localhost")

    communicator = WebsocketCommunicator(
        application,
        "/ws/tenant/",
        headers=[(b"host", b"tenant1.localhost")],
    )
    connected, subprotocol = await communicator.connect()

    assert connected

    # Send a message
    await communicator.send_json_to({"message": "hello"})

    # Receive the message
    response = await communicator.receive_json_from()
    assert response["message"] == "tenant1: hello"

    # Close the connection
    await communicator.disconnect()


@pytest.mark.xfail
@pytest.mark.asyncio
async def test_on_tenant_subfolder(tenant1, DomainModel):
    if DomainModel is None:
        pytest.skip("Domain model is not in use")

    await DomainModel.objects.acreate(tenant=tenant1, domain="tenants.localhost", folder="tenant1")

    communicator = WebsocketCommunicator(
        application,
        "/tenant1/ws/tenant/",
        headers=[(b"host", b"tenants.localhost")],
    )
    connected, subprotocol = await communicator.connect()

    assert connected

    # Send a message
    await communicator.send_json_to({"message": "hello"})

    # Receive the message
    response = await communicator.receive_json_from()
    assert response["message"] == "tenant1: hello"

    # Close the connection
    await communicator.disconnect()
