from django.test import Client, RequestFactory


def get_domain(tenant):
    if tenant.is_dynamic:
        return tenant.get_primary_domain().domain
    return tenant.domain_url or tenant.schema_name


class TenantRequestFactory(RequestFactory):
    def __init__(self, tenant, **defaults):
        super().__init__(**defaults)
        self.tenant = tenant

    def get(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_domain(self.tenant)
        return super().get(path, data, **extra)

    def post(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_domain(self.tenant)
        return super().post(path, data, **extra)

    def patch(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_domain(self.tenant)
        return super().patch(path, data, **extra)

    def put(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_domain(self.tenant)
        return super().put(path, data, **extra)

    def delete(self, path, data=None, content_type="application/octet-stream", **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_domain(self.tenant)
        return super().delete(path, data, **extra)


class TenantClient(Client):
    def __init__(self, tenant, enforce_csrf_checks=False, **defaults):
        super().__init__(enforce_csrf_checks, **defaults)
        self.tenant = tenant

    def get(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_domain(self.tenant)
        return super().get(path, data, **extra)

    def post(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_domain(self.tenant)
        return super().post(path, data, **extra)

    def patch(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_domain(self.tenant)
        return super().patch(path, data, **extra)

    def put(self, path, data=None, **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_domain(self.tenant)
        return super().put(path, data, **extra)

    def delete(self, path, data=None, content_type="application/octet-stream", **extra):
        if "HTTP_HOST" not in extra:
            extra["HTTP_HOST"] = get_domain(self.tenant)
        return super().delete(path, data, **extra)
