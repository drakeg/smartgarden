from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("gardens", "0010_podcarereminder"),
    ]

    operations = [
        migrations.CreateModel(
            name="PodHarvest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("plant_name", models.CharField(blank=True, max_length=120)),
                (
                    "harvested_at",
                    models.DateField(
                        db_index=True,
                        default=django.utils.timezone.localdate,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "unit",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("GRAM", "g"),
                            ("OUNCE", "oz"),
                            ("POUND", "lb"),
                            ("COUNT", "count"),
                        ],
                        max_length=12,
                    ),
                ),
                ("note", models.CharField(blank=True, max_length=240)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "pod",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="harvests",
                        to="gardens.pod",
                    ),
                ),
            ],
            options={
                "ordering": ["-harvested_at", "-created_at", "-id"],
            },
        ),
    ]
