from django.apps import apps
from django.conf import settings

from .schema import schema_handler
from .utils import get_tenant_database_alias


class SyncRouter(object):
    """
    A router to control which applications will be synced depending on the schema we're syncing.
    """

    def app_in_list(self, app_label, app_list):
        app_config = apps.get_app_config(app_label)
        app_config_full_name = "{}.{}".format(app_config.__module__, app_config.__class__.__name__)
        return (app_config.name in app_list) or (app_config_full_name in app_list)

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db != get_tenant_database_alias() or not schema_handler.active:
            return False
        app_list = []
        if schema_handler.active.schema_name == "public":
            app_list = settings.TENANTS["public"]["APPS"]
        elif schema_handler.active.schema_name in settings.TENANTS:
            app_list = settings.TENANTS[schema_handler.active.schema_name]["APPS"]
        else:
            app_list = settings.TENANTS["default"]["APPS"]
        if not app_list:
            return None
        return self.app_in_list(app_label, app_list)
