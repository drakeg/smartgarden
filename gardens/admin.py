from django.contrib import admin
from .models import Garden, Pod, PodNote

class PodInline(admin.TabularInline):
    model = Pod
    extra = 0

@admin.register(Garden)
class GardenAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "device_type", "is_public", "share_slug", "created_at")
    list_filter = ("device_type", "is_public")
    search_fields = ("name", "owner__username", "owner__email")
    inlines = [PodInline]

@admin.register(Pod)
class PodAdmin(admin.ModelAdmin):
    list_display = ("garden", "position", "plant_name", "status", "planted_at", "updated_at")
    list_filter = ("status", "garden__device_type")
    search_fields = ("plant_name", "garden__name")

@admin.register(PodNote)
class PodNoteAdmin(admin.ModelAdmin):
    list_display = ("pod", "created_at")
    search_fields = ("pod__plant_name", "note")

