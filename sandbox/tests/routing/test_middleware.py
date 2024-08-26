from itertools import permutations
from unittest.mock import MagicMock

import pytest
from django.http import Http404

from django_pgschemas.routing.info import DomainInfo, HeadersInfo, SessionInfo
from django_pgschemas.routing.middleware import (
    DomainRoutingMiddleware,
    HeadersRoutingMiddleware,
    SessionRoutingMiddleware,
    strip_tenant_from_path_factory,
)


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
        self.path = path
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
        if DomainModel is None:
            pytest.skip("Domain model is not in use")

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
    def test_tenant_matching(self, domain, path, schema_name, db):
        request = FakeRequest(domain=domain, path=f"/{path}/some/path/")
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


class TestDomainRoutingMiddlewareRedirection:
    @pytest.fixture(autouse=True)
    def _setup(self, tenant1, tenant2, DomainModel):
        if DomainModel is None:
            pytest.skip("Domain model is not in use")

        DomainModel(domain="tenant1.localhost", tenant=tenant1).save()
        DomainModel(
            domain="tenant1redirect.localhost",
            tenant=tenant1,
            is_primary=False,
            redirect_to_primary=True,
        ).save()
        DomainModel(
            domain="everyone.localhost",
            folder="tenant1redirect",
            tenant=tenant1,
            is_primary=False,
            redirect_to_primary=True,
        ).save()

        DomainModel(domain="everyone.localhost", folder="tenant2", tenant=tenant2).save()
        DomainModel(
            domain="tenant2redirect.localhost",
            tenant=tenant2,
            is_primary=False,
            redirect_to_primary=True,
        ).save()
        DomainModel(
            domain="everyone.localhost",
            folder="tenant2redirect",
            tenant=tenant2,
            is_primary=False,
            redirect_to_primary=True,
        ).save()

    @pytest.mark.parametrize(
        "domain, path, expected_redirection",
        [
            (
                "tenant1redirect.localhost",
                "/some/random/url/",
                "//tenant1.localhost/some/random/url/",
            ),
            (
                "everyone.localhost",
                "/tenant1redirect/some/random/url/",
                "//tenant1.localhost/some/random/url/",
            ),
            (
                "tenant2redirect.localhost",
                "/some/random/url/",
                "//everyone.localhost/tenant2/some/random/url/",
            ),
            (
                "everyone.localhost",
                "/tenant2redirect/some/random/url/",
                "//everyone.localhost/tenant2/some/random/url/",
            ),
        ],
    )
    def test_redirection(self, domain, path, expected_redirection):
        request = FakeRequest(domain=domain, path=path)
        get_response = MagicMock()

        response = DomainRoutingMiddleware(get_response)(request)

        assert response.status_code == 301
        assert response.url == expected_redirection
        assert response["Location"] == expected_redirection


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
    def test_tenant_matching(self, DomainModel, session_key, schema_name, db):
        if DomainModel is None and "tenant" in schema_name:
            pytest.skip("Domain model is not in use")

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
    def test_tenant_matching(self, DomainModel, header, schema_name, db):
        if DomainModel is None and "tenant" in schema_name:
            pytest.skip("Domain model is not in use")

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
    if DomainModel is None:
        pytest.skip("Domain model is not in use")

    DomainModel.objects.create(
        domain="tenants.localhost",
        tenant=tenant1,
        folder="tenant1",
        is_primary=True,
    )

    request = FakeRequest(
        domain="tenants.localhost",
        path="/tenant1/some/path/",
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
