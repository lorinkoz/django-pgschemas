from unittest.mock import patch

from django.apps import apps


@patch("django_pgschemas.checks.ensure_tenant_dict")
@patch("django_pgschemas.checks.ensure_public_schema")
@patch("django_pgschemas.checks.ensure_default_schemas")
@patch("django_pgschemas.checks.ensure_overall_schemas")
@patch("django_pgschemas.checks.ensure_extra_search_paths")
def test_all_checkers_called(*checkers):
    config = apps.get_app_config("django_pgschemas")

    config.ready()

    for checker in checkers:
        checker.assert_called()
