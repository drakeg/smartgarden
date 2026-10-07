from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("gardens", "0009_podplantingcycle"),
    ]

    operations = [
        migrations.CreateModel(
            name="PodCareReminder",
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
                ("title", models.CharField(max_length=160)),
                ("due_date", models.DateField(db_index=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "pod",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="care_reminders",
                        to="gardens.pod",
                    ),
                ),
            ],
            options={
                "ordering": ["completed_at", "due_date", "id"],
            },
        ),
    ]
