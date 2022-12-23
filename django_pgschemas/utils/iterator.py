from enum import NAMED_FLAGS, IntFlag, verify
from typing import Iterable, Optional

from django.conf import settings
from django.contrib.postgres.aggregates import ArrayAgg
from django.db.models import Case, CharField, F, OuterRef, Q, Subquery, Value, When

from ..schema import Schema
from .settings import get_clone_reference, get_domain_model, get_tenant_model


@verify(NAMED_FLAGS)
class SchemaClass(IntFlag):
    STATIC = 1
    DYNAMIC = 2
    CLONE_REFERENCE = 4

    TENANT_LIKE = DYNAMIC | CLONE_REFERENCE
    ALL = STATIC | TENANT_LIKE


def iterate_schemas(
    *,
    classes: Optional[SchemaClass] = None,
    identifiers: Optional[list[str]] = None,
    excluded_identifiers: Optional[list[str]] = None,
) -> Iterable[Schema]:
    if classes is None:
        classes = 0
    if identifiers is None:
        identifiers = []
    if excluded_identifiers is None:
        excluded_identifiers = []

    included_identifiers_set = set(identifiers)
    excluded_identifiers_set = set(excluded_identifiers)

    # If public is included, should always come first
    public_is_included = (classes & SchemaClass.STATIC) or ("public" in identifiers)
    public_is_also_excluded = "public" in excluded_identifiers
    if public_is_included and not public_is_also_excluded:
        yield Schema.create(schema_name="public")

    # Static schemas
    if classes & SchemaClass.STATIC or identifiers:
        for schema_name, data in settings.TENANTS.items():
            if schema_name in ["public", "default"]:
                continue

            local_identifiers = set([schema_name, *data["DOMAINS"]])

            if (
                classes & SchemaClass.STATIC or local_identifiers & included_identifiers_set
            ) and not local_identifiers & excluded_identifiers_set:
                yield Schema.create(schema_name, data["DOMAINS"][0])

    # Clone reference, if present
    if classes & SchemaClass.CLONE_REFERENCE:
        schema_name = get_clone_reference()
        if schema_name is not None:
            yield Schema.create(schema_name)

    # Dynamic schemas
    if classes & SchemaClass.DYNAMIC or identifiers:
        TenantModel = get_tenant_model()
        DomainModel = get_domain_model()

        tenant_qs = TenantModel._default_manager.annotate(
            domain_identifiers=ArrayAgg(
                Subquery(
                    DomainModel._default_manager.filter(tenant_id=OuterRef("pk"))
                    .order_by("-is_primary")
                    .annotate(
                        identifier=Case(
                            When(folder="", then=F("domain")),
                            default=F("domain") + Value("/") + F("folder"),
                            output_field=CharField(max_length=507),
                        )
                    )
                    .values("identifier")
                )
            )
        )

        if not classes & SchemaClass.DYNAMIC:
            tenant_qs = tenant_qs.filter(Q(schema_name__in=identifiers) | Q(domain_identifiers__overlap=identifiers))

        for tenant in tenant_qs.iterator(chunk_size=1000):
            domain_identifiers = tenant.domain_identifiers or []
            local_identifiers = set([tenant.schema_name, *domain_identifiers])

            if domain_identifiers:
                first_domain_identifier = domain_identifiers[0]
                tenant.domain, tenant.folder, *_ = first_domain_identifier.split("/") + [""]

            if not local_identifiers & excluded_identifiers_set:
                yield tenant
