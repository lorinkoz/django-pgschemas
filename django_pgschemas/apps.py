from django.apps import AppConfig as BaseAppConfig


class AppConfig(BaseAppConfig):
    name = "django_pgschemas"

    def ready(self) -> None:
        from . import checks  # noqa
        from .checks import (
            ensure_tenant_dict,
            ensure_public_schema,
            ensure_default_schemas,
            ensure_overall_schemas,
        )
        from .routing import middleware as _routing_middleware  # noqa: F401

        ensure_tenant_dict()
        ensure_public_schema()
        ensure_default_schemas()
        ensure_overall_schemas()
