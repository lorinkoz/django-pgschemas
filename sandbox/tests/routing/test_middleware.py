from itertools import permutations
from unittest.mock import MagicMock

import pytest
from django.http import Http404

from django_pgschemas.routing.info import DomainInfo, HeadersInfo, SessionInfo
from django_pgschemas.routing.middleware import (
    DomainRoutingMiddleware,
    HeadersRoutingMiddleware,
    SessionRoutingMiddleware,
    remove_www,
    strip_tenant_from_path_factory,
)


@pytest.mark.parametrize(
    "path, expected",
    [
        ("", ""),
        ("www", "www"),
        ("www.", ""),
        ("www.test.com", "test.com"),
        ("www.test.com/complex/path", "test.com/complex/path"),
        ("1www.test.com", "1www.test.com"),
    ],
)
def test_remove_www(path, expected):
    actual = remove_www(path)

    assert actual == expected


@pytest.mark.parametrize(
    "path, prefix, expected",
    [
        ("/some/path/", "", "/some/path/"),
        ("/some/path/", "path", "/some/path/"),
        ("/some/path/", "some", "/path/"),
    ],
)
def test_strip_tenant_from_path_factory(path, prefix, expected):
    actual = strip_tenant_from_path_factory(prefix)(path)

    assert actual == expected


class FakeRequest:
    def __init__(
        self,
        *,
        domain: str = "",
        path: str = "",
        session_tenant_ref: str | None = None,
        headers_tenant_ref: str | None = None,
    ) -> None:
        self.domain = domain
        self.path = f"/{path}/some/path/"
        self.session_tenant_ref = session_tenant_ref
        self.headers_tenant_ref = headers_tenant_ref

    def get_host(self) -> str:
        return self.domain

    @property
    def session(self) -> dict:
        return {
            "tenant": self.session_tenant_ref,
        }

    @property
    def headers(self) -> dict:
        return {
            "tenant": self.headers_tenant_ref,
        }


class TestDomainRoutingMiddleware:
    @pytest.fixture(autouse=True)
    def _setup(self, tenant1, tenant2, DomainModel):
        DomainModel.objects.create(
            tenant=tenant1,
            domain="tenant1.localhost",
            is_primary=True,
        )
        DomainModel.objects.create(
            tenant=tenant1,
            domain="tenants.localhost",
            folder="tenant1",
            is_primary=False,
        )
        DomainModel.objects.create(
            tenant=tenant2,
            domain="tenant2.localhost",
            is_primary=True,
        )
        DomainModel.objects.create(
            tenant=tenant2,
            domain="tenants.localhost",
            folder="tenant2",
            is_primary=False,
        )

    @pytest.mark.parametrize(
        "domain, path, schema_name",
        [
            ("tenant1.localhost", "", "tenant1"),
            ("tenants.localhost", "tenant1", "tenant1"),
            ("tenant2.localhost", "", "tenant2"),
            ("tenants.localhost", "tenant2", "tenant2"),
            ("tenant3.localhost", "", None),
            ("localhost", "", "www"),
            ("blog.localhost", "", "blog"),
            ("tenants.localhost", "", "www"),  # fallback domains
        ],
    )
    def test_tenant_matching(self, domain, path, schema_name):
        request = FakeRequest(domain=domain, path=path)
        get_response = MagicMock()

        handler = DomainRoutingMiddleware(get_response)

        if schema_name is None:
            with pytest.raises(Http404):
                handler(request)
        else:
            handler(request)
            assert request.tenant is not None
            assert request.tenant.schema_name == schema_name
            assert isinstance(request.tenant.routing, DomainInfo)
            assert request.tenant.routing.domain == domain
            assert request.tenant.routing.folder == (path if path else None)


class TestSessionRoutingMiddleware:
    @pytest.mark.parametrize(
        "session_key, schema_name",
        [
            ("www", "www"),
            ("main", "www"),
            ("blog", "blog"),
            ("tenant1", "tenant1"),
        ],
    )
    def test_tenant_matching(self, session_key, schema_name, db):
        request = FakeRequest(session_tenant_ref=session_key)
        get_response = MagicMock()

        handler = SessionRoutingMiddleware(get_response)

        handler(request)

        assert request.tenant is not None
        assert request.tenant.schema_name == schema_name
        assert isinstance(request.tenant.routing, SessionInfo)
        assert request.tenant.routing.reference == session_key


class TestHeadersRoutingMiddleware:
    @pytest.mark.parametrize(
        "header, schema_name",
        [
            ("www", "www"),
            ("main", "www"),
            ("blog", "blog"),
            ("tenant1", "tenant1"),
        ],
    )
    def test_tenant_matching(self, header, schema_name, db):
        request = FakeRequest(headers_tenant_ref=header)
        get_response = MagicMock()

        handler = HeadersRoutingMiddleware(get_response)

        handler(request)

        assert request.tenant is not None
        assert request.tenant.schema_name == schema_name
        assert isinstance(request.tenant.routing, HeadersInfo)
        assert request.tenant.routing.reference == header


@pytest.mark.parametrize(
    "first_middleware, second_middleware, last_middleware",
    permutations([DomainRoutingMiddleware, SessionRoutingMiddleware, HeadersRoutingMiddleware]),
)
def test_last_middleware_prevails(
    first_middleware, second_middleware, last_middleware, tenant1, tenant2, tenant3, DomainModel
):
    if DomainModel:
        DomainModel.objects.create(
            domain="tenants.localhost",
            tenant=tenant1,
            folder="tenant1",
            is_primary=True,
        )

    request = FakeRequest(
        domain="tenants.localhost",
        path="tenant1",
        session_tenant_ref=tenant2.schema_name,
        headers_tenant_ref=tenant3.schema_name,
    )
    get_response = MagicMock()

    handler = first_middleware(second_middleware(last_middleware(get_response)))

    handler(request)

    if last_middleware is DomainRoutingMiddleware:
        assert request.tenant == tenant1
        assert isinstance(request.tenant.routing, DomainInfo)

    if last_middleware is SessionRoutingMiddleware:
        assert request.tenant == tenant2
        assert isinstance(request.tenant.routing, SessionInfo)

    if last_middleware is HeadersRoutingMiddleware:
        assert request.tenant == tenant3
        assert isinstance(request.tenant.routing, HeadersInfo)
