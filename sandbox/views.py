from django.http import HttpResponse

RESPONSE_TEMPLATE = """
<dl>
    <dt>Path:</dt> <dd>{path}</dd>
    <dt>User:</dt> <dd>{user}</dd>
    <dt>Schema:</dt> <dd>{schema}</dd>
    <dt>Routing:</dt> <dd>{routing}</dd>
</dl>
"""


def generic(request):
    return HttpResponse(
        RESPONSE_TEMPLATE.format(
            path=request.get_full_path(),
            user=request.user,
            schema=request.tenant.schema_name,
            routing=request.tenant.routing,
        )
    )
