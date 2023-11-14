from importlib import import_module

from django.conf import settings

BASE_BACKEND = "django.db.backends.postgresql"
ORIGINAL_BACKEND = getattr(settings, "PGSCHEMAS_ORIGINAL_BACKEND", BASE_BACKEND)
EXTRA_SEARCH_PATHS = getattr(settings, "PGSCHEMAS_EXTRA_SEARCH_PATHS", [])

base_backend = import_module(BASE_BACKEND + ".base")
original_backend = import_module(ORIGINAL_BACKEND + ".base")
