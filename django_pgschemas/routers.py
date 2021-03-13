from django.apps import apps
from django.conf import settings

from .schema import get_current_schema
from .utils import get_tenant_database_alias


class SyncRouter:
    """
    A router to control which applications will be synced depending on the schema we're syncing.
    """

    def app_in_list(self, app_label, app_list):
        app_config = apps.get_app_config(app_label)
        app_config_full_name = f"{app_config.__module__}.{app_config.__class__.__name__}"
        return (app_config.name in app_list) or (app_config_full_name in app_list)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
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
