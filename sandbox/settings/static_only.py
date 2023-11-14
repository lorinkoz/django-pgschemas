from .base import *  # noqa: F403

TENANTS = {
    "public": {
        "APPS": [
            "shared_public",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
        ],
    },
    "www": {
        "APPS": ["shared_common", "app_main", "django.contrib.sessions"],
        "URLCONF": "app_main.urls",
        "WS_URLCONF": "app_main.ws_urls",
        "DOMAINS": ["localhost"],
        "FALLBACK_DOMAINS": ["everyone.localhost"],
    },
    "blog": {
        "APPS": ["shared_common", "app_blog", "django.contrib.sessions"],
        "URLCONF": "app_blog.urls",
        "DOMAINS": ["blog.localhost"],
    },
}

# Application definition

INSTALLED_APPS = ["django_pgschemas"]
for schema in TENANTS:
    INSTALLED_APPS += [app for app in TENANTS[schema]["APPS"] if app not in INSTALLED_APPS]

ROOT_URLCONF = TENANTS["www"]["URLCONF"]
