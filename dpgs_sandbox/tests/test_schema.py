from django.test import SimpleTestCase


class TestDeprecatedImports(SimpleTestCase):
    def test_schema_descriptor_warning(self):
        import warnings

        warnings.simplefilter("error")

        with self.assertRaises(DeprecationWarning) as ctx:
            from django_pgschemas.schema import SchemaDescriptor  # noqa

            self.assertEqual(str(ctx.exception), "'SchemaDescriptor' is deprecated, use 'Schema' instead")

    def test_schema_descriptor_accessible(self):
        from django_pgschemas.schema import SchemaDescriptor

        self.assertIsNotNone(SchemaDescriptor)
