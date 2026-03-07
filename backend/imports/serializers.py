from rest_framework import serializers

from .models import FestivalProImportSource, ImportRun, ImportSource


class FestivalProImportSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = FestivalProImportSource
        fields = [
            "login_url",
            "export_url",
            "export_body",
            "field_mappings",
        ]


class ImportSourceSerializer(serializers.ModelSerializer):
    username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    has_credentials = serializers.BooleanField(read_only=True)
    festivalpro_config = FestivalProImportSourceSerializer(required=False)

    class Meta:
        model = ImportSource
        fields = [
            "id",
            "name",
            "provider_type",
            "event",
            "has_credentials",
            "username",
            "password",
            "festivalpro_config",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "has_credentials", "created_at", "updated_at"]

    def create(self, validated_data):
        username = validated_data.pop("username", "")
        password = validated_data.pop("password", "")
        fp_data = validated_data.pop("festivalpro_config", None)

        source = ImportSource(**validated_data)
        if username or password:
            from .encryption import encrypt_credentials
            source.credentials = encrypt_credentials(username, password)
        source.save()

        if fp_data is not None:
            FestivalProImportSource.objects.create(source=source, **fp_data)
        elif source.provider_type == ImportSource.PROVIDER_FESTIVALPRO:
            # Create empty FP config automatically for FestivalPro sources
            FestivalProImportSource.objects.create(source=source)

        return source

    def update(self, instance, validated_data):
        username = validated_data.pop("username", None)
        password = validated_data.pop("password", None)
        fp_data = validated_data.pop("festivalpro_config", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Only update credentials if both fields explicitly provided
        if username is not None and password is not None:
            from .encryption import encrypt_credentials
            instance.credentials = encrypt_credentials(username, password)
        instance.save()

        # Update or create FP config
        if fp_data is not None:
            fp_config, _ = FestivalProImportSource.objects.get_or_create(source=instance)
            for attr, value in fp_data.items():
                setattr(fp_config, attr, value)
            fp_config.save()

        return instance


class ImportRunListSerializer(serializers.ModelSerializer):
    triggered_by_name = serializers.CharField(
        source="triggered_by.username", read_only=True, default=None
    )

    class Meta:
        model = ImportRun
        fields = [
            "id",
            "source",
            "triggered_by",
            "triggered_by_name",
            "status",
            "started_at",
            "finished_at",
            "source_file_name",
            "summary",
        ]
        read_only_fields = fields


class ImportRunSerializer(ImportRunListSerializer):
    """Full detail including per-booking log entries."""

    class Meta(ImportRunListSerializer.Meta):
        fields = ImportRunListSerializer.Meta.fields + ["log"]
        read_only_fields = fields
