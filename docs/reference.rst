Reference
=========

Models
------

``TenantMixin``
+++++++++++++++

.. autoclass:: django_pgschemas.models.TenantMixin
    :members: auto_create_schema, auto_drop_schema, create_schema, drop_schema

``DomainMixin``
+++++++++++++++

.. autoclass:: django_pgschemas.models.DomainMixin
    :members: absolute_url

Utils
-----

.. automodule:: django_pgschemas.utils
    :members: get_tenant_model, get_domain_model, is_valid_identifier,
        is_valid_schema_name, check_schema_name, remove_www,
        run_in_public_schema, schema_exists, dynamic_models_exist,
        create_schema, drop_schema, clone_schema, create_or_clone_schema

Signals
-------

.. autodata:: django_pgschemas.signals.schema_activate
.. autodata:: django_pgschemas.signals.dynamic_tenant_needs_sync
.. autodata:: django_pgschemas.signals.dynamic_tenant_post_sync
.. autodata:: django_pgschemas.signals.dynamic_tenant_pre_drop

URL resolvers
-------------

.. automodule:: django_pgschemas.urlresolvers
    :members: get_urlconf_from_schema
