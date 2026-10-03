from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("gardens", "0007_developeraccess"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DeveloperApiUsageDaily",
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
                ("usage_date", models.DateField(db_index=True)),
                (
                    "plan",
                    models.CharField(
                        choices=[
                            ("STARTER", "Starter"),
                            ("PRO", "Pro"),
                            ("ENTERPRISE", "Enterprise"),
                        ],
                        max_length=20,
                    ),
                ),
                ("request_count", models.PositiveBigIntegerField(default=0)),
                ("success_count", models.PositiveBigIntegerField(default=0)),
                ("client_error_count", models.PositiveBigIntegerField(default=0)),
                ("server_error_count", models.PositiveBigIntegerField(default=0)),
                ("last_request_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="developer_api_usage_daily",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-usage_date", "plan"],
            },
        ),
        migrations.AddConstraint(
            model_name="developerapiusagedaily",
            constraint=models.UniqueConstraint(
                fields=("user", "usage_date", "plan"),
                name="uniq_developer_usage_user_date_plan",
            ),
        ),
    ]
