Advanced configuration
======================

Fast dynamic tenant creation
----------------------------

Every time a instance of ``settings.TENANTS["default"]["TENANT_MODEL"]`` is
created, by default, the corresponding schema is created and synchronized
automatically. Depending on the number of migrations you already have in place,
or the amount of time these could take, or whether you need to pre-populate the
newly created schema with fixtures, this process could take a considerable
amount of time.

If you need a faster creation of dynamic schemas, you can do so by provisioning
a "reference" schema that can cloned into new schemas.

.. code-block:: python

    TENANTS = {
        # ...
        "default": {
            # ...
            "CLONE_REFERENCE": "sample",
        },
    }

Once you have this in your settings, you need to prepare your reference schema
with everything a newly created dynamic schema will need. The first step is
actually creating and synchronizing the reference schema. After that, you
can run any command on it, or edit its tables via ``shell``.

.. code-block:: bash

    python manage.py createrefschema
    python runschema loaddata tenant_app.products -s sample
    python runschema shell -s sample

The ``runschema`` command is explained in :ref:`running management commands`.

You don't need any extra step. As soon as a reference schema is configured,
next time you create an instance of the tenant model, it will clone the
reference schema instead of actually creating and synchronizing the schema.

Most importantly, by default, migrations will include the reference schema, so
that it is kept up to date for future tenant creation.


.. tip::

    The reference schema will get apps from
    ``settings.TENANTS["default"]["APPS"]`` and may look like any other dynamic
    tenant, but it is considered a *static* tenant instead, as there is no
    corresponding database entry for it. It's a special case of a static
    tenant, and it cannot be routed.

Fallback domains
----------------

If there is only one domain available, and no possibility to use subdomain
routing, the URLs for accessing your different tenants might look like::

    mydomain.com                -> main site
    mydomain.com/customer1      -> customer 1
    mydomain.com/customer2      -> customer 2

In this case, due to the order in which domains are tested, it is not possible
to put ``mydomain.com`` as domain for the main tenant without blocking all
dynamic schemas from getting routed. When
``django_pgschemas.middleware.TenantMiddleware`` is checking which tenant to
route from the incoming domain, it checks for static tenants first, then for
dynamic tenants. If ``mydomain.com`` is used for the main tenant (which is
static), then URLs like ``mydomain.com/customer1/some/url/`` will match the
main tenant always.

For a case like this, we provide a setting called ``FALLBACK_DOMAINS``. If no
tenant is found for an incoming combination of domain and subfolder, then,
static tenants are checked again for the fallback domains.

Something like this would be the proper configuration for the present case:

.. code-block:: python

    TENANTS = {
        "public": {
            "APPS": [
                "django.contrib.contenttypes",
                "django.contrib.staticfiles",
                # ...
                "django_pgschemas",
                "shared_app",
                # ...
            ],
        },
        "main": {
            "APPS": [
                "django.contrib.auth",
                "django.contrib.sessions",
                # ...
                "main_app",
            ],
            "DOMAINS": [],  # <--- No domain here
            "FALLBACK_DOMAINS": ["mydomain.com"], # <--- This is checked last
            "URLCONF": "main_app.urls",
        },
        "default": {
            "TENANT_MODEL": "shared_app.Client",
            "DOMAIN_MODEL": "shared_app.Domain",
            "APPS": [
                "django.contrib.auth",
                "django.contrib.sessions",
                # ...
                "tenant_app",
                # ...
            ],
            "URLCONF": "tenant_app.urls",
        }
    }

This example assumes that dynamic tenants will get their domains set to
``mydomain.com`` with a tenant specific subfolder, like ``client1`` or
``client2``.

Here, an incoming request for ``mydomain.com/client1/some/url/`` will fail for
the main tenant, then match against an existing dynamic tenant. On the other
hand, an incoming request for ``mydomain.com/some/url/`` will fail for all
static tenants, then fail for all dynamic tenants, and will finally match
against the fallback domains of the main tenant.

Static-only tenants
-------------------

It's also possible to have only static tenants. For this, the default key must
be omitted:

.. code-block:: python

    TENANTS = {
        "public": {
            "APPS": [
                "django.contrib.contenttypes",
                "django.contrib.staticfiles",
                # ...
                "django_pgschemas",
                "shared_app",
                # ...
            ],
        },
        "www": {
            "APPS": [
                "django.contrib.auth",
                "django.contrib.sessions",
                # ...
                "main_app",
            ],
            "DOMAINS": ["mydomain.com"],
            "URLCONF": "main_app.urls",
        },
        "blog": {
            "APPS": [
                "django.contrib.auth",
                "django.contrib.sessions",
                # ...
                "blog_app",
            ],
            "DOMAINS": ["blog.mydomain.com", "help.mydomain.com"],
            "URLCONF": "blog_app.urls",
        }
    }

In this case, no model is expected to inherit from ``TenantMixin`` and
``DomainMixin``, and no clone reference schema can be created.

Running management commands
---------------------------

Since all management commands occur outside the request/response cycle, all
commands from Django and any other third party apps are executed by default on
the public schema. In order to work around this, we provide a ``runschema``
command that accepts any other command to be run on one or multiple schemas. A
concise synopsis of the ``runschema`` command is as follows::

    usage: manage.py runschema [-s SCHEMAS [SCHEMAS ...]]
                            [-x EXCLUDED_SCHEMAS [EXCLUDED_SCHEMAS ...]]
                            [-as] [-ss] [-ds] [-ts]
                            [--parallel]
                            [--no-create-schemas]
                            [--noinput]
                            command_name

    Wrapper around django commands for use with an individual schema

    positional arguments:
    command_name          The command name you want to run

    optional arguments:

    --noinput, --no-input
                        Tells Django to NOT prompt the user for input of any
                        kind.

    -s SCHEMAS [SCHEMAS ...],
    --schema SCHEMAS [SCHEMAS ...]
                        Schema(s) to execute the current command
    -as, --include-all-schemas
                        Include all schemas when executing the current command
    -ss, --include-static-schemas
                        Include all static schemas when executing the current
                        command
    -ds, --include-dynamic-schemas
                        Include all dynamic schemas when executing the current
                        command
    -ts, --include-tenant-schemas
                        Include all tenant-like schemas when executing the
                        current command
    -x EXCLUDED_SCHEMAS [EXCLUDED_SCHEMAS ...],
    --exclude-schema EXCLUDED_SCHEMAS [EXCLUDED_SCHEMAS ...]
                        Schema(s) to exclude when executing the current
                        command

    --parallel          Run command in parallel mode
    --no-create-schemas
                        Skip automatic creation of non-existing schemas

The ``--schema`` parameter accepts multiple inputs of different kinds:

- The key of a static tenant or the ``schema_name`` of a dynamic tenant.
- The prefix of any domain, provided only one corresponding tenant is found.
- The ``domain/folder`` of a tenant, like ``customers.mydomain.com/client1``

The parameters ``-as``, ``-ss``, ``-ds`` and ``-ts`` act as wildcards for
including all schemas, static schemas, dynamic schemas and tenant-like schemas,
respectively. Tenant-like schemas are dynamic schemas plus the clone reference,
if it exists.

It's possible to exclude schemas via the ``-x`` parameter. Excluded schemas will
take precedence over included ones.

At least one schema is mandatory. If it's not provided with the command, either
explicitly or via wildcard params, it will be asked interactively. One notable
exception to this is when the option ``--noinput`` is passed, in which case the
command will fail.

If ``--parallel`` is passed, the command will be run asynchronously, spawning
multiple threads controlled by the setting ``PGSCHEMAS_PARALLEL_MAX_PROCESSES``.
It defaults to ``None``, in which case the number of CPUs will be used.

By default, schemas that do not exist will be created (but not synchronized),
except if ``--no-create-schemas`` is passed.

Full details for this command can be found in :ref:`runschema-cmd`.

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
    parameter ``tenant`` will be an instance of
    ``django_pgschemas.schema.Schema``. Make sure you do the
    appropriate type checking before accessing the tenant members, as not every
    tenant will be an instance of
    ``settings.TENANTS["default"]["TENANT_MODEL"]``.
