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

Tenant aware file system storage
--------------------------------

We provide a tenant aware file system storage at
``django_pgschemas.contrib.files.TenantFileSystemStorage``. It subclasses
``django.core.files.storage.FileSystemStorage`` and behaves like it in every
aspect, except that it prepends a tenant identifier to the path and URL of all
files.

By default, the tenant identifier is the schema name of the current tenant. In
order to override this behavior, it is possible to provide a different
identifier. The storage will consider these options when looking for an
identifier:

* A method called ``schema_pathname`` in the current tenant. This method must
  accept no arguments and return an identifier.
* A function specified in a setting called ``PGSCHEMAS_PATHNAME_FUNCTION``. This
  function must accept a schema descriptor and return an identifier.
* Finally, the identifier will default to the schema name of the current tenant.

In the case of the URL returned from the storage, if the storage detects that
the current schema has been routed via subfolder, it won't prepend the schema
identifier, because it considers that the path is properly disambiguated as is.
This means that instead of something like::

    /tenant1/static/tenant1/path/to/file.txt

It will generate::

    /tenant1/static/path/to/file.txt

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
