import os
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from django_pgschemas.contrib.files import TenantFileSystemStorage
from django_pgschemas.schema import Schema
from django_pgschemas.utils import get_tenant_model

TenantModel = get_tenant_model()


class TenantFileSystemStorageTestCase(TestCase):
    """
    Tests the tenant file system storage.
    """

    @classmethod
    def setUpClass(cls):
        cls.temp_dir = tempfile.mkdtemp()
        cls.storage = TenantFileSystemStorage(location=cls.temp_dir, base_url="/base-url/")

    @classmethod
    def tearDownClass(cls):
        if TenantModel is not None:
            for tenant in TenantModel.objects.all():
                tenant.delete(force_drop=True)
        shutil.rmtree(cls.temp_dir)

    def test_path_identifier_basic(self):
        with Schema.create(schema_name=""):
            self.assertEquals(self.storage.get_schema_path_identifier(), "")
        with Schema.create(schema_name="public"):
            self.assertEquals(self.storage.get_schema_path_identifier(), "public")
        with Schema.create(schema_name="blog"):
            self.assertEquals(self.storage.get_schema_path_identifier(), "blog")
        if TenantModel is not None:
            with TenantModel(schema_name="tenant"):
                self.assertEquals(self.storage.get_schema_path_identifier(), "tenant")

    def test_path_identifier_method_in_tenant(self):
        if TenantModel is not None:
            TenantModel.schema_pathname = lambda x: "custom-pathname"
            with TenantModel(schema_name="tenant"):
                self.assertEquals(self.storage.get_schema_path_identifier(), "custom-pathname")
            del TenantModel.schema_pathname

    def test_path_identifier_function_in_settings(self):
        if TenantModel is not None:
            with override_settings(
                PGSCHEMAS_PATHNAME_FUNCTION=lambda tenant: tenant.schema_name + "-custom-pathname"
            ):
                with TenantModel(schema_name="tenant"):
                    self.assertEquals(
                        self.storage.get_schema_path_identifier(), "tenant-custom-pathname"
                    )

    def test_base_location(self):
        with Schema.create(schema_name=""):
            self.assertEquals(self.storage.base_location, self.temp_dir + "/")
        with Schema.create(schema_name="public"):
            self.assertEquals(self.storage.base_location, self.temp_dir + "/public/")
        with Schema.create(schema_name="blog"):
            self.assertEquals(self.storage.base_location, self.temp_dir + "/blog/")
        if TenantModel is not None:
            with Schema.create(schema_name="tenant", folder="folder"):
                self.assertEquals(self.storage.base_location, self.temp_dir + "/tenant/")

    def test_base_url(self):
        with Schema.create(schema_name=""):
            self.assertEquals(self.storage.base_url, "/base-url/")
        with Schema.create(schema_name="public"):
            self.assertEquals(self.storage.base_url, "/base-url/public/")
        with Schema.create(schema_name="blog"):
            self.assertEquals(self.storage.base_url, "/base-url/blog/")
        if TenantModel is not None:
            with Schema.create(schema_name="tenant", folder="folder"):
                self.assertEquals(self.storage.base_url, "/base-url/")

    def test_file_path(self):
        if TenantModel is not None:
            self.assertFalse(self.storage.exists("test.file"))
            with Schema.create(schema_name="tenant1"):
                f = ContentFile("random content")
                f_name = self.storage.save("test.file", f)
                self.assertEqual(
                    os.path.join(self.temp_dir, "tenant1", f_name), self.storage.path(f_name)
                )
                self.storage.delete(f_name)
            self.assertFalse(self.storage.exists("test.file"))

    def test_file_save_with_path(self):
        if TenantModel is not None:
            self.assertFalse(self.storage.exists("path/to"))
            with Schema.create(schema_name="tenant1"):
                self.storage.save("path/to/test.file", ContentFile("file saved with path"))
                self.assertTrue(self.storage.exists("path/to"))
                with self.storage.open("path/to/test.file") as f:
                    self.assertEqual(f.read(), b"file saved with path")
                self.assertTrue(
                    os.path.exists(
                        os.path.join(self.temp_dir, "tenant1", "path", "to", "test.file")
                    )
                )
                self.storage.delete("path/to/test.file")
                self.assertFalse(self.storage.exists("test.file"))

    def test_file_url_simple(self):
        with Schema.create(schema_name=""):
            self.assertEqual(self.storage.url("test.file"), "/base-url/test.file")
        with Schema.create(schema_name="public"):
            self.assertEqual(self.storage.url("test.file"), "/base-url/public/test.file")
        if TenantModel is not None:
            with Schema.create(schema_name="tenant", folder="folder"):
                self.assertEqual(self.storage.url("test.file"), "/base-url/test.file")

    def test_file_url_complex(self):
        if TenantModel is not None:
            with Schema.create(schema_name="tenant"):
                self.assertEqual(
                    self.storage.url(r"~!*()'@#$%^&*abc`+ =.file"),
                    "/base-url/tenant/~!*()'%40%23%24%25%5E%26*abc%60%2B%20%3D.file",
                )
                self.assertEqual(self.storage.url("ab\0c"), "/base-url/tenant/ab%00c")
                self.assertEqual(self.storage.url("a/b\\c.file"), "/base-url/tenant/a/b/c.file")
                self.assertEqual(self.storage.url(""), "/base-url/tenant/")
                self.assertEqual(self.storage.url(None), "/base-url/tenant/")
