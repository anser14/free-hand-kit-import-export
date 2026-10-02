"""Adapter boundary around django-import-export resource construction."""

from __future__ import annotations

from typing import cast

from django.db.models import Field, Model
from import_export import fields, resources
from import_export.widgets import ForeignKeyWidget, ManyToManyWidget, Widget

from .conf import ResourceConfig, ResourceConfigurationError


def resource_class(config: ResourceConfig) -> type[resources.ModelResource[Model]]:
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
