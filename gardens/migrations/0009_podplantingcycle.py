from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("gardens", "0008_developerapiusagedaily"),
    ]

    operations = [
        migrations.CreateModel(
            name="PodPlantingCycle",
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
                ("planted_at", models.DateField(blank=True, null=True)),
                ("ended_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "final_status",
                    models.CharField(
                        choices=[
                            ("EMPTY", "Empty"),
                            ("SEEDED", "Seeded"),
                            ("SPROUTED", "Sprouted"),
                            ("GROWING", "Growing"),
                            ("HARVESTING", "Harvesting"),
                            ("REMOVED", "Removed"),
                        ],
                        default="EMPTY",
                        max_length=20,
                    ),
                ),
                (
                    "pod",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="planting_cycles",
                        to="gardens.pod",
                    ),
                ),
            ],
            options={
                "ordering": ["-ended_at", "-id"],
            },
        ),
    ]
