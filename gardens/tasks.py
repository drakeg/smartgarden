from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


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
