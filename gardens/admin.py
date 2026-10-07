from django.contrib import admin
from .models import DeveloperAccess, DeveloperApiUsageDaily, Garden, Pod, PodCareReminder, PodNote, PodPlantingCycle, GlobalNote

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

@admin.register(PodCareReminder)
class PodCareReminderAdmin(admin.ModelAdmin):
    list_display = ("title", "pod", "due_date", "completed_at", "created_at")
    list_filter = ("due_date", "completed_at")
    search_fields = ("title", "pod__plant_name", "pod__garden__name")


@admin.register(PodNote)
class PodNoteAdmin(admin.ModelAdmin):
    list_display = ("pod", "created_at")
    search_fields = ("pod__plant_name", "note")


@admin.register(GlobalNote)
class GlobalNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "created_at")
    search_fields = ("title", "note", "author__username")



@admin.register(DeveloperAccess)
class DeveloperAccessAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "status", "billing_provider", "access_expires_at", "updated_at")
    list_filter = ("plan", "status", "billing_provider")
    search_fields = ("user__username", "user__email", "billing_customer_id", "billing_subscription_id")


@admin.register(DeveloperApiUsageDaily)
class DeveloperApiUsageDailyAdmin(admin.ModelAdmin):
    list_display = (
        "usage_date",
        "user",
        "plan",
        "request_count",
        "success_count",
        "client_error_count",
        "server_error_count",
        "last_request_at",
    )
    list_filter = ("plan", "usage_date")
    search_fields = ("user__username", "user__email")
    date_hierarchy = "usage_date"
    readonly_fields = (
        "user",
        "usage_date",
        "plan",
        "request_count",
        "success_count",
        "client_error_count",
        "server_error_count",
        "last_request_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PodPlantingCycle)
class PodPlantingCycleAdmin(admin.ModelAdmin):
    list_display = ("pod", "plant_name", "planted_at", "final_status", "ended_at")
    list_filter = ("final_status", "ended_at")
    search_fields = ("pod__garden__name", "pod__plant_name", "plant_name")
    readonly_fields = ("pod", "plant_name", "planted_at", "final_status", "ended_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
