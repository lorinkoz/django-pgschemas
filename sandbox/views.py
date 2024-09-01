from django.shortcuts import render
from django.urls import reverse


def generic(request):
    context = {
        "path": request.get_full_path(),
        "user": request.user,
        "schema": request.tenant.schema_name,
        "routing": request.tenant.routing,
        "ping_url": reverse("ping"),
    }
    return render(request, "index.html", context)
