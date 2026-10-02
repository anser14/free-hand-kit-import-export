"""OpenAPI serializers for the resource-discovery foundation endpoints."""

from __future__ import annotations

from rest_framework import serializers


class ResourceSerializer(serializers.Serializer[dict[str, object]]):
    key = serializers.CharField()
    model = serializers.CharField()
    import_fields = serializers.ListField(child=serializers.CharField())
    export_fields = serializers.ListField(child=serializers.CharField())
    import_id_fields = serializers.ListField(child=serializers.CharField())
    search_fields = serializers.ListField(child=serializers.CharField())
    ordering_fields = serializers.ListField(child=serializers.CharField())
    filter_fields = serializers.ListField(child=serializers.CharField())


class ResourceSchemaSerializer(ResourceSerializer):
    relationships = serializers.DictField(child=serializers.DictField())
    operations = serializers.ListField(child=serializers.CharField())
