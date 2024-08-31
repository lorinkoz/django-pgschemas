import pytest
from channels.testing import WebsocketCommunicator

from sandbox.routing import domain_application, headers_application


@pytest.mark.asyncio
async def test_on_main_domain():
    communicator = WebsocketCommunicator(
        domain_application,
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
async def test_on_tenant_subdomain(tenant3, DomainModel):
    if DomainModel is None:
        pytest.skip("Domain model is not in use")

    await DomainModel.objects.acreate(tenant=tenant3, domain="ws_tenant3.localhost")

    communicator = WebsocketCommunicator(
        domain_application,
        "/ws/tenant/",
        headers=[(b"host", b"ws_tenant3.localhost")],
    )
    connected, subprotocol = await communicator.connect()

    assert connected

    # Send a message
    await communicator.send_json_to({"message": "hello"})

    # Receive the message
    response = await communicator.receive_json_from()
    assert response["message"] == "tenant3: hello"

    # Close the connection
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_on_tenant_subfolder(tenant3, DomainModel):
    if DomainModel is None:
        pytest.skip("Domain model is not in use")

    await DomainModel.objects.acreate(
        tenant=tenant3, domain="ws_tenants.localhost", folder="tenant3"
    )

    communicator = WebsocketCommunicator(
        domain_application,
        "/tenant3/ws/tenant/",
        headers=[(b"host", b"ws_tenants.localhost")],
    )
    connected, subprotocol = await communicator.connect()

    assert connected

    # Send a message
    await communicator.send_json_to({"message": "hello"})

    # Receive the message
    response = await communicator.receive_json_from()
    assert response["message"] == "tenant3: hello"

    # Close the connection
    await communicator.disconnect()


@pytest.mark.asyncio
async def test_on_main_header():
    communicator = WebsocketCommunicator(
        headers_application,
        "/ws/main/",
        headers=[(b"tenant", b"main")],
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
async def test_on_tenant_header(TenantModel, db):
    if TenantModel is None:
        pytest.skip("Dynamic tenants are not in use")

    communicator = WebsocketCommunicator(
        headers_application,
        "/ws/tenant/",
        headers=[(b"tenant", b"tenant3")],
    )
    connected, subprotocol = await communicator.connect()

    assert connected

    # Send a message
    await communicator.send_json_to({"message": "hello"})

    # Receive the message
    response = await communicator.receive_json_from()
    assert response["message"] == "tenant3: hello"

    # Close the connection
    await communicator.disconnect()
