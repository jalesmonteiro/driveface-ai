from rest_framework import serializers
from .models import Cluster, Face, Identity, Photo


class ClusterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cluster
        fields = (
            "id",
            "album",
            "identity",
            "label",
            "avatar_crop_webp",
            "face_count",
            "is_suggested",
            "created_at",
        )
        read_only_fields = ("id", "avatar_crop_webp", "face_count", "created_at")


class IdentitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Identity
        fields = ("id", "user", "person_name", "total_samples", "updated_at")
        read_only_fields = ("id", "user", "total_samples", "updated_at")


class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ("id", "album", "google_file_id", "filename", "faces_count")


class FaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Face
        fields = (
            "id",
            "photo",
            "cluster",
            "bbox_xmin",
            "bbox_ymin",
            "bbox_xmax",
            "bbox_ymax",
            "detection_confidence",
        )
