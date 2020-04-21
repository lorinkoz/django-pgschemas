from django.apps import apps
from django.conf import settings
from django.core import checks
from django.test import TestCase, override_settings

from django_pgschemas.checks import check_apps, get_user_app


class AppConfigTestCase(TestCase):
    """
    Tests TENANTS settings is properly defined.
    """

    def setUp(self):
        self.app_config = apps.get_app_config("django_pgschemas")

    def test_contenttypes_location(self):
        with override_settings(TENANTS={"default": {"APPS": ["django.contrib.contenttypes"]}}):
            errors = check_apps(self.app_config)
            expected_errors = [
                checks.Warning(
                    "'django.contrib.contenttypes' in TENANTS['default']['APPS'] must be on 'public' schema only.",
                    id="pgschemas.W001",
                )
            ]
            self.assertEqual(errors, expected_errors)
        with override_settings(TENANTS={"default": {}, "www": {"APPS": ["django.contrib.contenttypes"]}}):
            errors = check_apps(self.app_config)
            expected_errors = [
                checks.Warning(
                    "'django.contrib.contenttypes' in TENANTS['www']['APPS'] must be on 'public' schema only.",
                    id="pgschemas.W001",
                )
            ]
            self.assertEqual(errors, expected_errors)

    def test_user_session_location(self):
        user_app = get_user_app()

        with override_settings(TENANTS={"default": {"APPS": ["django.contrib.sessions"]}}):
            errors = check_apps(self.app_config)
            expected_errors = [
                checks.Warning(
                    "'%s' must be together with '%s' in TENANTS['%s']['APPS']."
                    % (user_app, "django.contrib.sessions", "default"),
                    id="pgschemas.W002",
                )
            ]
            self.assertEqual(errors, expected_errors)
        with override_settings(
            TENANTS={
                "default": {"APPS": ["shared_common"]},
                "www": {"APPS": ["shared_common", "django.contrib.sessions"]},
            }
        ):
            errors = check_apps(self.app_config)
            expected_errors = [
                checks.Warning(
                    "'%s' must be together with '%s' in TENANTS['%s']['APPS']."
                    % ("django.contrib.sessions", user_app, "default"),
                    id="pgschemas.W002",
                )
            ]
            self.assertEqual(errors, expected_errors)
