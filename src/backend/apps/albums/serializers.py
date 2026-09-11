from rest_framework import serializers
from .models import Album, AlbumShare, Job


class AlbumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Album
        fields = (
            "id",
            "owner",
            "google_drive_folder_id",
            "folder_name",
            "share_token",
            "is_share_active",
            "created_at",
            "last_synced_at",
        )
        read_only_fields = ("id", "owner", "share_token", "created_at", "last_synced_at")


class ProcessAlbumSerializer(serializers.Serializer):
    google_drive_folder_id = serializers.CharField(max_length=255)
    folder_name = serializers.CharField(max_length=255)


class JobStatusSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = (
            "id",
            "status",
            "total_images",
            "processed_images",
            "progress_percentage",
            "error_message",
            "clustering_metrics",
            "started_at",
            "finished_at",
        )

    def get_progress_percentage(self, obj) -> float:
        if obj.total_images == 0:
            return 0.0
        return round((obj.processed_images / obj.total_images) * 100.0, 1)


class AlbumShareSerializer(serializers.ModelSerializer):
    invite_type_display = serializers.CharField(source="get_invite_type_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = AlbumShare
        fields = (
            "id",
            "invited_email",
            "role",
            "invite_type",
            "invite_type_display",
            "status",
            "status_display",
            "invited_at",
            "updated_at",
        )
        read_only_fields = ("id", "role", "invited_at", "updated_at")
