"""Declarative authorization and direct owner/tenant scope resolution."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast

from django.contrib.auth.models import AbstractBaseUser
from django.core.checks import Error
from django.db.models import Model, QuerySet
from django.utils.module_loading import import_string

from .conf import ResourceConfig, ResourceConfigurationError, ScopeConfig


class ScopeResolutionError(ValueError):
    """Raised when a configured scope cannot be resolved safely for a user."""


class ResourcePolicy:
    """Host extension point for indirect tenancy and other domain-specific access rules.

    Configure a zero-argument subclass through a resource's ``POLICY`` import path.
    The policy is composed with the package's direct ``SCOPE`` constraint; it never
    replaces resource permissions or permits undeclared resource fields.
    """

    def filter_queryset(
        self,
        *,
        queryset: QuerySet[Model],
        user: AbstractBaseUser,
        operation: str,
    ) -> QuerySet[Model]:
        """Return the records the user may access for READ, EXPORT, or IMPORT."""

        return queryset

    def prepare_instance(self, *, instance: Model, user: AbstractBaseUser) -> None:
        """Set or validate scalar host state before model validation and save."""


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


def get_resource_policy(resource: ResourceConfig) -> ResourcePolicy | None:
    """Load the explicitly configured host policy and require the stable base class."""

    if resource.policy_path is None:
        return None
    try:
        policy_class = import_string(resource.policy_path)
        policy = policy_class()
    except Exception as exc:
        raise ResourceConfigurationError(
            f"Resource '{resource.key}' POLICY '{resource.policy_path}' could not be loaded."
        ) from exc
    if not isinstance(policy, ResourcePolicy):
        raise ResourceConfigurationError(
            f"Resource '{resource.key}' POLICY must subclass "
            "fk_import_export.policies.ResourcePolicy."
        )
    return policy


def policy_configuration_issues(resource: ResourceConfig) -> list[Error]:
    """Return an actionable system-check error for an invalid host policy class."""

    try:
        get_resource_policy(resource)
    except ResourceConfigurationError as exc:
        return [Error(str(exc), id="fk_import_export.E023")]
    return []


def _apply_policy_queryset(
    *,
    policy: ResourcePolicy,
    resource: ResourceConfig,
    queryset: QuerySet[Model],
    user: AbstractBaseUser,
    operation: str,
) -> QuerySet[Model]:
    """Apply a host policy while enforcing that it cannot switch resource models."""

    filtered = policy.filter_queryset(queryset=queryset, user=user, operation=operation)
    if not isinstance(filtered, QuerySet) or filtered.model is not resource.model():
        raise ResourceConfigurationError(
            f"Resource '{resource.key}' POLICY must return a queryset for {resource.model_label}."
        )
    return filtered


def scoped_queryset(
    *, resource: ResourceConfig, user: AbstractBaseUser, operation: str
) -> tuple[QuerySet[Model], ResolvedScope | None, ResourcePolicy | None]:
    """Return an approved queryset constrained by direct scope and the host policy."""

    scope = resolve_scope(scope=resource.scope, user=user)
    queryset = resource.model()._default_manager.all()
    if scope is not None:
        queryset = queryset.filter(**{scope.model_field: scope.value})
    policy = get_resource_policy(resource)
    if policy is not None:
        queryset = _apply_policy_queryset(
            policy=policy,
            resource=resource,
            queryset=queryset,
            user=user,
            operation=operation,
        )
    return queryset, scope, policy


def apply_import_policy(
    *,
    policy: ResourcePolicy | None,
    resource: ResourceConfig,
    queryset: QuerySet[Model],
    user: AbstractBaseUser,
) -> QuerySet[Model]:
    """Apply the configured policy to import identity lookups."""

    if policy is None:
        return queryset
    return _apply_policy_queryset(
        policy=policy,
        resource=resource,
        queryset=queryset,
        user=user,
        operation="IMPORT",
    )
