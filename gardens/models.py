from django.conf import settings
from django.db import models, IntegrityError, transaction
from django.utils import timezone
import secrets

class DeviceType(models.TextChoices):
    AHOPEGARDEN_12 = "AHOPEGARDEN_12", "Ahopegarden 12 Pod"

class PodStatus(models.TextChoices):
    EMPTY = "EMPTY", "Empty"
    SEEDED = "SEEDED", "Seeded"
    SPROUTED = "SPROUTED", "Sprouted"
    GROWING = "GROWING", "Growing"
    HARVESTING = "HARVESTING", "Harvesting"
    REMOVED = "REMOVED", "Removed"

class Garden(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="gardens"
    )

    guest_token = models.CharField(max_length=64, blank=True, db_index=True)
    is_guest = models.BooleanField(default=False)
    name = models.CharField(max_length=120)
    device_type = models.CharField(max_length=40, choices=DeviceType.choices, default=DeviceType.AHOPEGARDEN_12)

    is_public = models.BooleanField(default=False)
    share_slug = models.SlugField(max_length=32, unique=True, blank=True, null=True)

    view_front = models.CharField(
        max_length=10,
        choices=[("left", "Left"), ("right", "Right")],
        default="left"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def ensure_share_slug(self) -> None:
        if self.share_slug:
            return

        # Retry a few times in case of collision (very rare)
        for _ in range(10):
            candidate = secrets.token_urlsafe(8).replace("-", "").replace("_", "")
            self.share_slug = candidate
            try:
                with transaction.atomic():
                    self.save(update_fields=["share_slug"])
                return
            except IntegrityError:
                self.share_slug = None

        raise RuntimeError("Unable to generate a unique share slug.")

    def __str__(self) -> str:
        return f"{self.name}"

class Pod(models.Model):
    garden = models.ForeignKey(Garden, on_delete=models.CASCADE, related_name="pods")
    position = models.PositiveSmallIntegerField()  # 1..12
    plant_name = models.CharField(max_length=120, blank=True)
    planted_at = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=PodStatus.choices, default=PodStatus.EMPTY)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("garden", "position")
        ordering = ["position"]

    def days_growing(self) -> int | None:
        if not self.planted_at:
            return None
        return (timezone.localdate() - self.planted_at).days

    def display_label(self) -> str:
        return self.plant_name.strip() or "—"

    def __str__(self) -> str:
        return f"{self.garden.name} Pod {self.position}"

class PodNote(models.Model):
    pod = models.ForeignKey(Pod, on_delete=models.CASCADE, related_name="notes")
    created_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField()
    photo = models.ImageField(upload_to="pod_photos/", blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Note for {self.pod} @ {self.created_at}"

