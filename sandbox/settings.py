"""
Django settings for sandbox project.

Generated by 'django-admin startproject' using Django 2.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "asd#$#ae)^gegm6m9omvic^ct@*@bkf!0afe*+4h$5-zmf^h&$u4(1vr"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = [".localhost"]

TENANTS = {
    "public": {
        "APPS": [
            "sandbox.shared_public",
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.staticfiles",
        ],
    },
    "www": {
        "APPS": [
            "sandbox.shared_common",
            "sandbox.app_main",
            "django.contrib.sessions",
        ],
        "URLCONF": "sandbox.app_main.urls",
        "WS_URLCONF": "sandbox.app_main.ws_urls",
        "DOMAINS": ["localhost"],
        "SESSION_KEY": "main",
        "HEADER": "main",
        "FALLBACK_DOMAINS": ["tenants.localhost"],
    },
    "blog": {
        "APPS": [
            "sandbox.shared_common",
            "sandbox.app_blog",
            "django.contrib.sessions",
        ],
        "URLCONF": "sandbox.app_blog.urls",
        "DOMAINS": ["blog.localhost"],
    },
    "default": {
        "TENANT_MODEL": "shared_public.Tenant",
        "DOMAIN_MODEL": "shared_public.Domain",
        "APPS": [
            "sandbox.shared_common",
            "sandbox.app_tenants",
            "django.contrib.sessions",
        ],
        "URLCONF": "sandbox.app_tenants.urls",
        "WS_URLCONF": "sandbox.app_tenants.ws_urls",
        "CLONE_REFERENCE": "sample",
    },
}

# Application definition

INSTALLED_APPS = ["django_pgschemas"]
for schema in TENANTS:
    INSTALLED_APPS += [app for app in TENANTS[schema]["APPS"] if app not in INSTALLED_APPS]

ROOT_URLCONF = TENANTS["default"]["URLCONF"]

ASGI_APPLICATION = "routing.application"

AUTH_USER_MODEL = "shared_common.User"
LOGIN_URL = "login"

MIDDLEWARE = [
    "django_pgschemas.routing.middleware.DomainRoutingMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django_pgschemas.postgresql",
        "NAME": "sandbox",
        "USER": "postgres",
        "PASSWORD": os.environ.get("DATABASE_PASSWORD", "postgres"),
        "HOST": os.environ.get("DATABASE_HOST", "localhost"),
        "PORT": "",
    }
}

DATABASE_ROUTERS = ("django_pgschemas.routers.SyncRouter",)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "KEY_FUNCTION": "django_pgschemas.contrib.cache.make_key",
    }
}


# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True


USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/

STATIC_URL = "/static/"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
