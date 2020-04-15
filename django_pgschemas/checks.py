from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.base_session import AbstractBaseSession
from django.core import checks
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_module


def get_user_app():
    try:
        return get_user_model()._meta.app_config.name
    except ImproperlyConfigured:
        return None


def get_session_app():
    engine = import_module(settings.SESSION_ENGINE)
    store = engine.SessionStore
    if hasattr(store, "get_model_class"):
        session_model = store.get_model_class()
        if issubclass(session_model, AbstractBaseSession):
            return session_model._meta.app_config.name
    return None


@checks.register()
def check_apps(app_configs, **kwargs):
    errors = []
    user_app = get_user_app()
    session_app = get_session_app()
    if "django.contrib.contenttypes" in settings.TENANTS["default"].get("APPS", []):
        errors.append(
            checks.Warning(
                "'django.contrib.contenttypes' in TENANTS['default']['APPS'] must be on 'public' schema only.",
                id="pgschemas.W001",
            )
        )
    for schema in settings.TENANTS:
        schema_apps = settings.TENANTS[schema].get("APPS", [])
        if schema not in ["public", "default"]:
            if "django.contrib.contenttypes" in schema_apps:
                errors.append(
                    checks.Warning(
                        "'django.contrib.contenttypes' in TENANTS['%s']['APPS'] must be on 'public' schema only."
                        % schema,
                        id="pgschemas.W001",
                    )
                )
        if user_app and session_app:
            if session_app in schema_apps and user_app not in schema_apps:
                errors.append(
                    checks.Warning(
                        "'%s' must be together with '%s' in TENANTS['%s']['APPS']." % (user_app, session_app, schema),
                        id="pgschemas.W002",
                    )
                )
            elif user_app in schema_apps and session_app not in schema_apps and session_app in settings.INSTALLED_APPS:
                errors.append(
                    checks.Warning(
                        "'%s' must be together with '%s' in TENANTS['%s']['APPS']." % (session_app, user_app, schema),
                        id="pgschemas.W002",
                    )
                )
    return errors
