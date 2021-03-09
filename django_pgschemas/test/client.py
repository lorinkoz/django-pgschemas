from django.test import Client, RequestFactory


def get_host(tenant, caller):
    host = tenant.domain_url
    if hasattr(tenant, "get_primary_domain"):
        primary_domain = tenant.get_primary_domain()
        if primary_domain:
            host = primary_domain.domain
    assert host is not None, "%s must be used in the context of an active tenant with an inferrable domain" % type(
        caller
    )
    return host


class TenantRequestFactory(RequestFactory):
    def __init__(self, tenant, **defaults):
        super().__init__(**defaults)
        self.tenant = tenant

    def get(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_host(self.tenant, self)
        return super().get(path, data, **extra)

    def post(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_host(self.tenant, self)
        return super().post(path, data, **extra)

    def patch(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_host(self.tenant, self)
        return super().patch(path, data, **extra)

    def put(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_host(self.tenant, self)
        return super().put(path, data, **extra)

    def delete(self, path, data=None, content_type="application/octet-stream", **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_host(self.tenant, self)
        return super().delete(path, data, **extra)


class TenantClient(Client):
    def __init__(self, tenant, enforce_csrf_checks=False, **defaults):
        super().__init__(enforce_csrf_checks, **defaults)
        self.tenant = tenant

    def get(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_host(self.tenant, self)
        return super().get(path, data, **extra)

    def post(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_host(self.tenant, self)
        return super().post(path, data, **extra)

    def patch(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_host(self.tenant, self)
        return super().patch(path, data, **extra)

    def put(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_host(self.tenant, self)
        return super().put(path, data, **extra)

    def delete(self, path, data=None, content_type="application/octet-stream", **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_host(self.tenant, self)
        return super().delete(path, data, **extra)
