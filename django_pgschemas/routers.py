from typing import Iterable

from django.apps import apps
from django.conf import settings

from django_pgschemas.schema import get_current_schema
from django_pgschemas.utils import get_tenant_database_alias


class TenantAppsRouter:
    """
    A router to control which applications will be actually migrated depending on the schema.
    """

    def app_in_list(self, app_label: str, app_list: Iterable) -> bool:
        app_config = apps.get_app_config(app_label)
        app_config_full_name = f"{app_config.__module__}.{app_config.__class__.__name__}"
        return (app_config.name in app_list) or (app_config_full_name in app_list)

    def allow_migrate(
        self, db: str, app_label: str, model_name: str | None = None, **hints: object
    ) -> bool | None:
        current_schema = get_current_schema()
        if db != get_tenant_database_alias() or current_schema is None:
            return False
        app_list = []
        if current_schema.schema_name == "public":
            app_list = settings.TENANTS["public"]["APPS"]
        elif current_schema.schema_name in settings.TENANTS:
            app_list = settings.TENANTS[current_schema.schema_name]["APPS"]
        else:
            app_list = settings.TENANTS["default"]["APPS"]
        if not app_list:
            return None
        return self.app_in_list(app_label, app_list)
