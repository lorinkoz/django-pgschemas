from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import checks


@checks.register()
def check_apps(app_configs):
    errors = []
    user_app = get_user_model()._meta.app_config.name
    if "django.contrib.contenttypes" in settings.TENANTS["default"].get("APPS", []):
        errors.append(checks.Warning("'django.contrib.contenttypes' must be on 'public' schema.", id="pgschemas.W001",))
    for schema in settings.TENANTS:
        schema_apps = settings.TENANTS[schema].get("APPS", [])
        if ("django.contrib.sessions" in schema_apps and user_app not in schema_apps) or (
            user_app in schema_apps and "django.contrib.sessions" not in schema_apps
        ):
            errors.append(
                checks.Warning(
                    "'django.contrib.sessions' must be on schemas that also have '%s'." % user_app, id="pgschemas.W002",
                )
            )
        if schema not in ["public", "default"]:
            if "django.contrib.contenttypes" in schema_apps:
                errors.append(
                    checks.Warning("'django.contrib.contenttypes' must be on 'public' schema.", id="pgschemas.W001",)
                )
    return errors
