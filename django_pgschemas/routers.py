from django.apps import apps
from django.conf import settings

from .schema import schema_handler
from .utils import get_clone_reference


class SyncRouter(object):
    """
    A router to control which applications will be synced depending on the schema we're syncing.
    It also controls database for read/write in a tenant sharding configuration.
    """

    def app_in_list(self, app_label, app_list):
        app_config = apps.get_app_config(app_label)
        app_config_full_name = "{}.{}".format(app_config.__module__, app_config.__class__.__name__)
        return (app_config.name in app_list) or (app_config_full_name in app_list)

    def db_for_read(self, model, **hints):
        if not schema_handler.active or schema_handler.active.schema_name in ["public", get_clone_reference()]:
            return None
        return schema_handler.active.get_database()

    def db_for_write(self, model, **hints):
        if not schema_handler.active or schema_handler.active.schema_name in ["public", get_clone_reference()]:
            return None
        return schema_handler.active.get_database()

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if not schema_handler.active:
            return False
        app_list = []
        databases = []
        if schema_handler.active.schema_name == "public":
            app_list = settings.TENANTS["public"]["APPS"]
            databases = settings.TENANTS["public"].get("DATABASES") or ["default"]
        elif schema_handler.active.schema_name in settings.TENANTS:
            app_list = settings.TENANTS[schema_handler.active.schema_name]["APPS"]
            databases = settings.TENANTS[schema_handler.active.schema_name].get("DATABASES") or ["default"]
        else:
            app_list = settings.TENANTS["default"]["APPS"]
            databases = settings.TENANTS["default"].get("DATABASES") or ["default"]
        if not app_list or not databases:
            return None
        return db in databases and self.app_in_list(app_label, app_list)
