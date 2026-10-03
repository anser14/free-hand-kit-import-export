"""Example host policies used to exercise the public Freehand Kit policy contract."""

from django.contrib.auth.models import AbstractBaseUser
from django.core.exceptions import ValidationError
from django.db.models import Model, QuerySet

from fk_import_export.policies import ResourcePolicy


class ApprovedSkuPolicy(ResourcePolicy):
    """Expose and allow imports only for the host-approved SKU namespace."""

    def filter_queryset(
        self,
        *,
        queryset: QuerySet[Model],
        user: AbstractBaseUser,
        operation: str,
    ) -> QuerySet[Model]:
        return queryset.filter(sku__startswith="APPROVED-")

    def prepare_instance(self, *, instance: Model, user: AbstractBaseUser) -> None:
        if not str(instance.sku).startswith("APPROVED-"):
            raise ValidationError({"sku": "SKU is outside the approved namespace."})


class NotAPolicy:
    """Intentionally invalid configuration target for system-check coverage."""
