from django.apps import AppConfig


class DjangoPgSchemasConfig(AppConfig):
    name = "django_pgschemas"

    def ready(self) -> None:
        from . import checks  # noqa
        from .checks import (
            ensure_tenant_dict,
            ensure_public_schema,
            ensure_default_schemas,
            ensure_overall_schemas,
            ensure_extra_search_paths,
        )

        ensure_tenant_dict()
        ensure_public_schema()
        ensure_default_schemas()
        ensure_overall_schemas()
        ensure_extra_search_paths()
