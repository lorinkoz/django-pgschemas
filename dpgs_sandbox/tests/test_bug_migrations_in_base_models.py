from django.apps import apps
from django.core import management
from django.test import TransactionTestCase, tag

from django_pgschemas.checks import check_schema_names


@tag("bug")
class BaseMigrationsTestCase(TransactionTestCase):
    """
    Tests the migrate command in situations where accesing the base models could
    raise ProgrammingError.
    """

    def setUp(self):
        self.app_config = apps.get_app_config("django_pgschemas")

    def test_zero_migrate(self):
        management.call_command("migrate", "shared_public", "zero", verbosity=0)
        # The goal is that the next line doesn't raise ProgrammingError
        check_schema_names(self.app_config)
        management.call_command("migrate", verbosity=0)
