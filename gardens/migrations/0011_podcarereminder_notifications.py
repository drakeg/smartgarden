from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gardens", "0010_podcarereminder"),
    ]

    operations = [
        migrations.AddField(
            model_name="podcarereminder",
            name="email_notification_enabled",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="podcarereminder",
            name="last_notified_on",
            field=models.DateField(blank=True, null=True),
        ),
    ]
