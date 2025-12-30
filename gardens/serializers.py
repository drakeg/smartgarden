from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Garden, Pod, PodNote, GlobalNote


user_model = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = user_model
        fields = ("id", "username", "email")


class PodNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PodNote
        fields = ("id", "pod", "created_at", "note", "photo")


class PodSerializer(serializers.ModelSerializer):
    notes = PodNoteSerializer(many=True, read_only=True)

    class Meta:
        model = Pod
        fields = ("id", "garden", "position", "plant_name", "planted_at", "status", "updated_at", "notes")


class GardenSerializer(serializers.ModelSerializer):
    pods = PodSerializer(many=True, read_only=True)
    owner = UserSerializer(read_only=True)

    class Meta:
        model = Garden
        fields = ("id", "owner", "name", "device_type", "is_public", "share_slug", "view_front", "created_at", "pods")


class GlobalNoteSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = GlobalNote
        fields = ("id", "created_at", "author", "title", "note")
