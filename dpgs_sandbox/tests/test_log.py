from django.test import TestCase

from django_pgschemas.log import SchemaContextFilter
from django_pgschemas.schema import Schema


class SchemaContextFilterTestCase(TestCase):
    """
    Tests SchemaContextFilter.
    """

    def test_filter(self):
        class FakeRecord:
            pass

        record = FakeRecord()
        scf = SchemaContextFilter()
        with Schema.create(schema_name="some-tenant", domain_url="some-tenant.some-url.com"):
            scf.filter(record)
        self.assertEqual(record.schema_name, "some-tenant")
        self.assertEqual(record.domain_url, "some-tenant.some-url.com")
