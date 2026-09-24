from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("gardens", "0006_globalnote"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DeveloperAccess",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("plan", models.CharField(choices=[("STARTER", "Starter"), ("PRO", "Pro"), ("ENTERPRISE", "Enterprise")], default="STARTER", max_length=20)),
                ("status", models.CharField(choices=[("INACTIVE", "Inactive"), ("ACTIVE", "Active"), ("PAST_DUE", "Past due"), ("CANCELED", "Canceled")], default="INACTIVE", max_length=20)),
                ("billing_provider", models.CharField(blank=True, max_length=40)),
                ("billing_customer_id", models.CharField(blank=True, max_length=120)),
                ("billing_subscription_id", models.CharField(blank=True, max_length=120)),
                ("access_expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="developer_access", to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
