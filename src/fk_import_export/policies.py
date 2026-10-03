"""Declarative authorization and direct owner/tenant scope resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Model, QuerySet

from .conf import ResourceConfig, ScopeConfig


class ScopeResolutionError(ValueError):
    """Raised when a configured scope cannot be resolved safely for a user."""


class PermissionUser(Protocol):
    """The authenticated-user contract needed by Django permission policies."""

    is_staff: bool

    def has_perm(self, perm: str, obj: object | None = None) -> bool: ...


@dataclass(frozen=True)
class ResolvedScope:
    """A validated direct model lookup bound to one authenticated user value."""

    model_field: str
    value: object


def _requirements_for(resource: ResourceConfig, operation: str) -> tuple[str, ...]:
    if operation == "READ":
        return resource.permissions.read
    if operation == "EXPORT":
        return resource.permissions.export
    if operation == "IMPORT":
        return resource.permissions.import_
    raise ValueError(f"Unsupported resource operation '{operation}'.")


def has_resource_permission(
    *, resource: ResourceConfig, user: AbstractBaseUser, operation: str
) -> bool:
    """Return whether every configured requirement permits this resource operation."""

    permission_user = cast(PermissionUser, user)
    for requirement in _requirements_for(resource, operation):
        if requirement == "$staff":
            if not permission_user.is_staff:
                return False
        elif not permission_user.has_perm(requirement):
            return False
    return True


def resolve_scope(*, scope: ScopeConfig | None, user: AbstractBaseUser) -> ResolvedScope | None:
    """Resolve a direct configured user field without evaluating arbitrary code or paths."""

    if scope is None:
        return None
    try:
        value = user if scope.user_attribute == "$self" else getattr(user, scope.user_attribute)
    except AttributeError as exc:
        raise ScopeResolutionError(
            f"The current user cannot resolve required scope attribute '{scope.user_attribute}'."
        ) from exc
    if value is None:
        raise ScopeResolutionError(
            f"The current user has no value for required scope attribute '{scope.user_attribute}'."
        )
    return ResolvedScope(model_field=scope.model_field, value=value)


def scoped_queryset(
    *, resource: ResourceConfig, user: AbstractBaseUser
) -> tuple[QuerySet[Model], ResolvedScope | None]:
    """Return an approved resource queryset constrained to the caller's direct scope."""

    scope = resolve_scope(scope=resource.scope, user=user)
    queryset = resource.model()._default_manager.all()
    if scope is not None:
        queryset = queryset.filter(**{scope.model_field: scope.value})
    return queryset, scope
