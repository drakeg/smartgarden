from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import Garden, Pod, PodCareReminder, PodNote, PodPlantingCycle, GlobalNote


user_model = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = user_model
        fields = ("id", "username", "email")


class PodNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PodNote
        fields = ("id", "pod", "created_at", "note", "photo")


class PodCareReminderSerializer(serializers.ModelSerializer):
    is_completed = serializers.BooleanField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)

    class Meta:
        model = PodCareReminder
        fields = (
            "id",
            "title",
            "due_date",
            "completed_at",
            "email_notification_enabled",
            "last_notified_on",
            "created_at",
            "is_completed",
            "is_overdue",
        )
        read_only_fields = fields


class PodPlantingCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PodPlantingCycle
        fields = (
            "id",
            "plant_name",
            "planted_at",
            "final_status",
            "ended_at",
        )
        read_only_fields = fields


class PodSerializer(serializers.ModelSerializer):
    notes = PodNoteSerializer(many=True, read_only=True)
    planting_cycles = PodPlantingCycleSerializer(many=True, read_only=True)
    care_reminders = PodCareReminderSerializer(many=True, read_only=True)

    class Meta:
        model = Pod
        fields = ("id", "garden", "position", "plant_name", "planted_at", "status", "updated_at", "notes", "planting_cycles", "care_reminders")


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
