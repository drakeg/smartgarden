from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import PodCareReminder


def send_templated_email(subject: str, recipient: str, template_name: str, context: dict) -> None:
    text_body = render_to_string(f"emails/{template_name}.txt", context).strip()
    html_body = render_to_string(f"emails/{template_name}.html", context)
    email = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[recipient],
    )
    email.attach_alternative(html_body, "text/html")
    email.send()


@shared_task(name="gardens.send_templated_email")
def send_templated_email_task(
    subject: str,
    recipient: str,
    template_name: str,
    context: dict,
) -> None:
    send_templated_email(subject, recipient, template_name, context)


def queue_or_send_templated_email(
    subject: str,
    recipient: str,
    template_name: str,
    context: dict,
) -> None:
    if getattr(settings, "CELERY_BROKER_URL", ""):
        send_templated_email_task.delay(subject, recipient, template_name, context)
        return

    send_templated_email(subject, recipient, template_name, context)


@shared_task(name="gardens.send_due_care_reminder_digests")
def send_due_care_reminder_digests() -> int:
    """Email one due/overdue care-reminder digest per opted-in account."""
    if not getattr(settings, "CARE_REMINDER_EMAILS_ENABLED", False):
        return 0

    today = timezone.localdate()
    reminders = (
        PodCareReminder.objects.filter(
            email_notification_enabled=True,
            completed_at__isnull=True,
            due_date__lte=today,
            pod__garden__is_guest=False,
            pod__garden__owner__is_active=True,
        )
        .exclude(last_notified_on=today)
        .exclude(pod__garden__owner__email="")
        .select_related("pod__garden__owner", "pod__garden")
        .order_by("pod__garden__owner_id", "due_date", "pod__garden__name", "pod__position")
    )

    grouped: dict[int, list[PodCareReminder]] = {}
    for reminder in reminders:
        grouped.setdefault(reminder.pod.garden.owner_id, []).append(reminder)

    sent = 0
    site_base_url = getattr(settings, "SITE_BASE_URL", "").rstrip("/")
    for account_reminders in grouped.values():
        owner = account_reminders[0].pod.garden.owner
        context = {
            "user": owner,
            "reminders": account_reminders,
            "today": today,
            "site_base_url": site_base_url,
        }
        send_templated_email(
            "Smart Garden care reminders due",
            owner.email,
            "care_reminder_digest",
            context,
        )
        PodCareReminder.objects.filter(
            pk__in=[reminder.pk for reminder in account_reminders]
        ).update(last_notified_on=today)
        sent += 1

    return sent
