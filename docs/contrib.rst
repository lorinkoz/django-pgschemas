Contributions
=============

All contributions and third party integrations live inside
``django_pgschemas.contrib``.

If you want to implement an integration with other Django packages, please
submit a pull request containing:

* The code for your integration
* The tests for your integration
* The docs for your integration in this section of the documentation

We're striving to maintain/increase our code coverage, but please, make sure your
integration is properly tested. Proper tests will always beat meaningless 100%
coverage.

Channels (websockets)
---------------------

We provide a tenant aware protocol router for using with ``channels``. You can
use it as follows:

.. code-block:: python

    # routing.py

    from django_pgschemas.contrib.channels import TenantProtocolRouter

    application = TenantProtocolRouter()

    # settings.py

    ASGI_APPLICATION = "routing.application"

It requires that you also route the websockets requests, at least for the
dynamic tenants. If you don't route websocket requests for static tenants, the
dynamic route will be used:

.. code-block:: python

    TENANTS = {
        # ...
        "default": {
            # ...
            "URLCONF": "tenant_app.urls",
            "WS_URLCONF": "tenant_app.ws_urls",
        }
    }

You still need to name your channel groups appropriately, taking the
current tenant into account if you want to keep your groups tenant-specific.
You will get the current tenant in ``scope["tenant"]``.
