from django.conf import settings
from django.urls import reverse

from django_pgschemas.routing.info import DomainInfo
from django_pgschemas.routing.urlresolvers import get_dynamic_tenant_prefixed_urlconf


def test_no_tenant():
    url = reverse("profile")

    assert url == "/profile/"


def test_tenant_with_no_folder(tenant1):
    with tenant1:
        url = reverse("profile")

    assert url == "/profile/"


def test_tenant_with_folder(tenant1):
    tenant1.routing = DomainInfo(domain="irrelevant", folder="tenant1")

    dynamic_path = settings.ROOT_URLCONF + "_dynamically_tenant_prefixed"
    urlconf = get_dynamic_tenant_prefixed_urlconf(settings.ROOT_URLCONF, dynamic_path)

    with tenant1:
        url = reverse("profile", urlconf=urlconf)

    tenant1.routing = None

    assert url == "/tenant1/profile/"
