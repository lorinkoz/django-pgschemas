from importlib import import_module

from django.conf import settings

ORIGINAL_BACKEND = getattr(settings, "PGSCHEMAS_ORIGINAL_BACKEND", "django.db.backends.postgresql")
EXTRA_SEARCH_PATHS = getattr(settings, "PGSCHEMAS_EXTRA_SEARCH_PATHS", [])

original_backend = import_module(ORIGINAL_BACKEND + ".base")
