from django.http import HttpResponse

RESPONSE_TEMPLATE = """
Path: {path}
User: {user}
Schema: {schema}
Domain: {domain}
Folder: {folder}
"""


def generic(request):
    return HttpResponse(
        RESPONSE_TEMPLATE.format(
            path=request.get_full_path(),
            user=request.user,
            schema=request.tenant.schema_name,
            domain=request.tenant.domain_url,
            folder=request.tenant.folder,
        )
    )
