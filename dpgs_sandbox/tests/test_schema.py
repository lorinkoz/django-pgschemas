import warnings

from django.test import SimpleTestCase


class TestDeprecatedImports(SimpleTestCase):
    def test_schema_descriptor_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            from django_pgschemas.schema import SchemaDescriptor  # noqa

            self.assertEqual(len(w), 1)
            self.assertEqual(
                str(w[0].message), "'SchemaDescriptor' is deprecated, use 'Schema' instead"
            )

    def test_schema_descriptor_accessible(self):
        from django_pgschemas.schema import SchemaDescriptor

        self.assertIsNotNone(SchemaDescriptor)
