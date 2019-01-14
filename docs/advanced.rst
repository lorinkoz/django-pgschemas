Advanced configuration
======================

Management commands
-------------------

Since all management commands occur outside the request/response cycle, all
commands from Django and any other third party apps are executed by default on
the public schema. In order to work around this, we provide a ``runschema``
command that accepts any other command to be run on one or multiple schemas::

    usage: manage.py runschema [-h] [--version] [-v {0,1,2,3}]
                            [--settings SETTINGS] [--pythonpath PYTHONPATH]
                            [--traceback] [--no-color] [--noinput] [-s SCHEMA]
                            [--executor {sequential,parallel}]
                            [--no-create-schemas]
                            command_name

    Wrapper around django commands for use with an individual schema

    positional arguments:
    command_name          The command name you want to run

    optional arguments:
    --noinput, --no-input
                            Tells Django to NOT prompt the user for input of any
                            kind.
    -s SCHEMA, --schema SCHEMA
                            Schema to execute the current command
    --executor {sequential,parallel}
                            Executor to be used for running command on schemas
    --no-create-schemas   Skip automatic creation of non-existing schemas

The schema parameter accepts multiple inputs:

- The key of a static tenant or the ``schema_name`` of a dynamic tenant.
- The prefix of any domain, provided only one corresponding tenant is found.
- The ``domain/folder`` of a tenant, like ``customers.mydomain.com/client1``
- The wildcards ``:all:``, ``:static:`` and ``:dynamic:``.

The schema is mandatory. If it's not provided with the command, it will be
asked interactively, except if ``--noinput`` is passed, in which case the
command will fail.

The executor argument accepts two options:

:sequential:
    Will run the command synchronously, one schema at a time. This is the
    default executor.

:parallel:
    Will run the command asynchronously, spawning multiple threads controlled
    by the setting ``PGSCHEMAS_PARALLEL_MAX_PROCESSES``. It defaults to
    ``None``, in which case the number of CPUs will be used.

By default, schemas that do not exist will be created (but not synchronized),
except if ``--no-create-schemas`` is passed.

Inheritable commands
++++++++++++++++++++

We also provide some base commands you can inherit, in order to mimic the
behavior of ``runschema``. By inheriting these you will get the parameters
we discussed in the previous section. The base commands provide a
``handle_tenant`` you must override in order to execute the actions you need
on any given tenant.

The base commands are:

.. code-block:: python

    # django_pgschemas.management.commands.__init__.py

    class TenantCommand(WrappedSchemaOption, BaseCommand):
        # ...

        def handle_tenant(self, tenant, *args, **options):
            pass

    class StaticTenantCommand(TenantCommand):
        # ...

    class DynamicTenantCommand(TenantCommand):
        # ...

.. attention::

    Since these commands can work with both static and dynamic tenants, the
    parameter ``tenant`` could be an instance of
    ``settings.TENANTS["public"]["TENANT_MODEL"]`` or
    ``django_pgschemas.schema.SchemaDescriptor``. Make sure you do the
    appropriate type checking before accessing the tenant members.

Caching
-------

In order to generate tenant aware cache keys, you can use
``django_pgschemas.cache.make_key`` as your ``KEY_FUNCTION``:

.. code-block:: python

    CACHES = {
        "default": {
            # ...
            "KEY_FUNCTION": "django_pgschemas.cache.make_key",
        }
    }

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
