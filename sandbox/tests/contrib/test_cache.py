from django_pgschemas.contrib.cache import make_key, reverse_key
from django_pgschemas.schema import Schema


def test_make_key_with_dynamic_tenant(tenant1):
    with tenant1:
        key = make_key(key="foo", key_prefix="", version=1)

    chunks = key.split(":")

    assert len(chunks) == 4
    assert str(tenant1.schema_name) == chunks[0]


def test_make_key_with_static_tenant():
    with Schema.create(schema_name="www"):
        key = make_key(key="foo", key_prefix="", version=1)

    chunks = key.split(":")

    assert len(chunks) == 4
    assert "www" == chunks[0]


def test_reverse_key(tenant1):
    key = "some-key"

    with tenant1:
        assert key == reverse_key(make_key(key=key, key_prefix="", version=1))
