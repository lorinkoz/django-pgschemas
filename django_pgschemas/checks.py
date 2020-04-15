from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.base_session import AbstractBaseSession
from django.core import checks


def get_session_apps():
    session_apps = set()
    for app_config in apps.get_app_configs():
        for model in app_config.get_models():
            if issubclass(model, AbstractBaseSession):
                session_apps.add(model._meta.app_config.name)
    return session_apps


@checks.register()
def check_apps(app_configs, **kwargs):
    errors = []
    user_app = get_user_model()._meta.app_config.name
    session_apps = list(get_session_apps())
    if "django.contrib.contenttypes" in settings.TENANTS["default"].get("APPS", []):
        errors.append(checks.Warning("'django.contrib.contenttypes' must be on 'public' schema.", id="pgschemas.W001",))
    for schema in settings.TENANTS:
        schema_apps = settings.TENANTS[schema].get("APPS", [])
        if schema not in ["public", "default"]:
            if "django.contrib.contenttypes" in schema_apps:
                errors.append(
                    checks.Warning("'django.contrib.contenttypes' must be on 'public' schema.", id="pgschemas.W001",)
                )
        for session_app in session_apps:
            if (session_app in schema_apps and user_app not in schema_apps) or (
                user_app in schema_apps and session_app not in schema_apps and session_app in settings.INSTALLED_APPS
            ):
                errors.append(
                    checks.Warning(
                        "'%s' must be on schemas that also have '%s'." % (session_app, user_app), id="pgschemas.W002",
                    )
                )
    return errors
