import kopf
import smtplib
import base64
import logging
from email.message import EmailMessage
from kubernetes import client

logger = logging.getLogger(__name__)


def get_smtp_credentials(secret_name, namespace):
    # Get the Kubernetes API client
    api = client.CoreV1Api()

    try:
        secret = api.read_namespaced_secret(secret_name, namespace)
    except client.exceptions.ApiException as e:
        raise kopf.TemporaryError(f"Failed to read secret: {e}", delay=30)

    # Extract and decode secret values
    username_b64 = secret.data.get("SMTP_USERNAME")
    password_b64 = secret.data.get("SMTP_PASSWORD")

    if not username_b64 or not password_b64:
        raise kopf.TemporaryError("Secret missing required keys", delay=30)

    username = base64.b64decode(username_b64).decode("utf-8")
    password = base64.b64decode(password_b64).decode("utf-8")

    return username, password


def send_notification(message, spec, namespace):
    smtp_from = spec.get("smtpFrom")
    smtp_to = spec.get("smtpTo")
    smtp_host = spec.get("smtpHost")
    smtp_port = spec.get("smtpPort")
    secret_name = spec.get("secretName")

    if not smtp_from:
        raise kopf.TemporaryError(f"For notification smtpFrom must be set. Got {smtp_from!r}.")
    if not smtp_to:
        raise kopf.TemporaryError(f"For notification smtpTo must be set. Got {smtp_to!r}.")
    if not smtp_host:
        raise kopf.TemporaryError(f"For notification smtpHost must be set. Got {smtp_host!r}.")
    if not smtp_port:
        raise kopf.TemporaryError(f"For notification smtpPort must be set. Got {smtp_port!r}.")

    subject = "Notification from Checkmydump"

    # Compose the email
    msg = EmailMessage()
    msg["From"] = smtp_from
    msg["To"] = smtp_to
    msg["Subject"] = subject
    msg.set_content(message)

    # Get login credentials from secret
    smtp_username, smtp_password = get_smtp_credentials(secret_name, namespace)

    if not smtp_password or not smtp_username:
        raise kopf.PermanentError("Missing all the required credentials for the notification via email.")

    # Send the email using SMTP
    with smtplib.SMTP_SSL(smtp_host, smtp_port) as smtp:
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(msg)

    logging.info(f"Email sent to {smtp_to}!")
