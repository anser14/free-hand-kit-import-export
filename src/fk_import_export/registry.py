"""Adapter boundary around django-import-export resource construction."""

from __future__ import annotations

from typing import cast

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Field, Model
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget, Widget

from .conf import ResourceConfig, ResourceConfigurationError
from .policies import ResolvedScope, ResourcePolicy, apply_import_policy


def resource_class(
    config: ResourceConfig,
    *,
    scope: ResolvedScope | None = None,
    policy: ResourcePolicy | None = None,
    user: AbstractBaseUser | None = None,
) -> type[resources.ModelResource[Model]]:
    """Build a configured ``ModelResource`` without host boilerplate classes.

    This private adapter is deliberately the only place that depends on
    django-import-export's resource API. A future engine can preserve the public
    Freehand resource contract while replacing this implementation.
    """

    model = config.model()
    selected_fields = tuple(dict.fromkeys((*config.import_fields, *config.export_fields)))
    meta = type(
        "Meta",
        (),
        {
            "model": model,
            "fields": selected_fields,
            "import_id_fields": config.import_id_fields,
            "use_transactions": True,
            "clean_model_instances": True,
        },
    )
    attributes: dict[str, object] = {"Meta": meta}

    policy_user: AbstractBaseUser | None = None
    if policy is not None:
        if not isinstance(user, AbstractBaseUser):
            raise ResourceConfigurationError(
                f"Resource '{config.key}' POLICY requires an authenticated user."
            )
        policy_user = user

    if scope is not None or policy is not None:

        def get_queryset(self):  # type: ignore[no-untyped-def]
            queryset = super(type(self), self).get_queryset()
            if scope is not None:
                queryset = queryset.filter(**{scope.model_field: scope.value})
            if policy is not None and policy_user is not None:
                queryset = apply_import_policy(
                    policy=policy,
                    resource=config,
                    queryset=queryset,
                    user=policy_user,
                )
            return queryset

        def before_save_instance(self, instance, row, **kwargs):  # type: ignore[no-untyped-def]
            if scope is not None:
                setattr(instance, scope.model_field, scope.value)
            if policy is not None and policy_user is not None:
                policy.prepare_instance(instance=instance, user=policy_user)

        attributes["get_queryset"] = get_queryset
        attributes["before_save_instance"] = before_save_instance

    for field_name in selected_fields:
        model_field = model._meta.get_field(field_name)
        if (
            isinstance(model_field, Field)
            and model_field.is_relation
            and field_name not in config.relations
        ):
            raise ResourceConfigurationError(
                f"Resource '{config.key}' relation '{field_name}' requires explicit "
                "RELATIONS lookup configuration."
            )

    for relation_name, relation in config.relations.items():
        relation_field = model._meta.get_field(relation_name)
        if not isinstance(relation_field, Field) or not relation_field.is_relation:
            raise ResourceConfigurationError(
                f"Resource '{config.key}' relation '{relation_name}' is not a forward relation."
            )
        related_model = relation_field.related_model
        if related_model is None:
            raise ResourceConfigurationError(
                f"Resource '{config.key}' relation '{relation_name}' has no related model."
            )
        widget: Widget
        if relation_field.many_to_many:
            # The runtime constructor requires the model class; the external
            # stub currently annotates this parameter as a model instance.
            widget = ManyToManyWidget(
                cast(Model, related_model),
                field=relation.lookup_field,
                separator=relation.separator,
            )
        else:
            widget = ForeignKeyWidget(related_model, field=relation.lookup_field)
        attributes[relation_name] = fields.Field(
            column_name=relation_name,
            attribute=relation_name,
            widget=widget,
        )

    return type(f"{config.key.title()}FreehandResource", (resources.ModelResource,), attributes)
