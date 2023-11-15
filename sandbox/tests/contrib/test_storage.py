import os
import shutil
import tempfile

import pytest
from django.core.files.base import ContentFile

from django_pgschemas.contrib.storage import TenantFileSystemStorage
from django_pgschemas.routing.info import DomainInfo
from django_pgschemas.schema import Schema

STORAGE_BASE_URL = "/base-url/"


@pytest.fixture
def temp_dir():
    value = tempfile.mkdtemp()

    yield value

    shutil.rmtree(value)


@pytest.fixture
def storage(temp_dir):
    return TenantFileSystemStorage(location=temp_dir, base_url=STORAGE_BASE_URL)


@pytest.fixture
def settings_pathname(settings):
    settings.PGSCHEMAS_PATHNAME_FUNCTION = lambda tenant: f"custom-pathname-{tenant.schema_name}"


class TestPathIdentifier:
    def test_basic_dynamic(self, storage, tenant1):
        with tenant1:
            assert storage.get_schema_path_identifier() == tenant1.schema_name

    def test_basic_static(self, storage):
        with Schema.create(schema_name="www"):
            assert storage.get_schema_path_identifier() == "www"

    def test_method_in_tenant(self, storage, tenant1):
        tenant1.schema_pathname = lambda: "custom-pathname"
        with tenant1:
            assert storage.get_schema_path_identifier() == "custom-pathname"
        del tenant1.schema_pathname

    def test_function_in_settings(self, tenant1, storage, settings_pathname):
        with tenant1:
            assert storage.get_schema_path_identifier() == f"custom-pathname-{tenant1.schema_name}"


def test_base_location(storage, temp_dir, tenant1, settings_pathname):
    with tenant1:
        assert storage.base_location == f"{temp_dir}/custom-pathname-{tenant1.schema_name}/"


def test_base_url(storage, tenant1):
    tenant1.routing = DomainInfo(domain="irrelevant", folder="tenant1")

    with tenant1:
        assert storage.base_url == STORAGE_BASE_URL

    tenant1.routing = None


def test_file_path(storage, temp_dir, tenant1):
    assert not storage.exists("test.file")

    with tenant1:
        f = ContentFile("random content")
        f_name = storage.save("test.file", f)

        assert os.path.join(temp_dir, tenant1.schema_name, f_name) == storage.path(f_name)

        storage.delete(f_name)

    assert not storage.exists("test.file")


def test_file_save_with_path(storage, temp_dir, tenant1):
    assert not storage.exists("path/to")

    with tenant1:
        storage.save("path/to/test.file", ContentFile("file saved with path"))

        assert storage.exists("path/to")

        with storage.open("path/to/test.file") as f:
            assert f.read() == b"file saved with path"

        assert os.path.exists(
            os.path.join(temp_dir, tenant1.schema_name, "path", "to", "test.file")
        )

        storage.delete("path/to/test.file")

    assert not storage.exists("test.file")


def test_file_url_simple(storage, tenant1):
    tenant1.routing = DomainInfo(domain="irrelevant", folder="tenant1")

    with tenant1:
        assert storage.url("test.file") == "/base-url/test.file"

    tenant1.routing = None


def test_file_url_complex(storage, tenant1):
    with tenant1:
        assert (
            storage.url(r"~!*()'@#$%^&*abc`+ =.file")
            == f"/base-url/{tenant1.schema_name}/~!*()'%40%23%24%25%5E%26*abc%60%2B%20%3D.file"
        )
        assert storage.url("ab\0c") == f"/base-url/{tenant1.schema_name}/ab%00c"
        assert storage.url("a/b\\c.file") == f"/base-url/{tenant1.schema_name}/a/b/c.file"
        assert storage.url("") == f"/base-url/{tenant1.schema_name}/"
        assert storage.url(None) == f"/base-url/{tenant1.schema_name}/"
