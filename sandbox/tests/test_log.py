from django_pgschemas.log import SchemaContextFilter
from django_pgschemas.routing.info import DomainInfo, HeadersInfo, SessionInfo
from django_pgschemas.schema import Schema


class FakeRecord:
    pass


class TestSchemaContextFilter:
    def test_filter_with_domain(self):
        record = FakeRecord()
        scf = SchemaContextFilter()

        with Schema.create(
            schema_name="some-tenant",
            routing=DomainInfo(
                domain="some-tenant.some-url.com",
                folder="folder1",
            ),
        ):
            scf.filter(record)

        assert record.schema_name == "some-tenant"
        assert record.domain == "some-tenant.some-url.com"
        assert record.folder == "folder1"

    def test_filter_with_session(self):
        record = FakeRecord()
        scf = SchemaContextFilter()

        with Schema.create(
            schema_name="some-tenant",
            routing=SessionInfo(reference="tenant1"),
        ):
            scf.filter(record)

        assert record.schema_name == "some-tenant"
        assert record.reference == "tenant1"

    def test_filter_with_header(self):
        record = FakeRecord()
        scf = SchemaContextFilter()

        with Schema.create(
            schema_name="some-tenant",
            routing=HeadersInfo(reference="tenant1"),
        ):
            scf.filter(record)

        assert record.schema_name == "some-tenant"
        assert record.reference == "tenant1"
