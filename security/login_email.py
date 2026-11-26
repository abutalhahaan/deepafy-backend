import logging

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


logger = logging.getLogger(__name__)


LOGIN_ALERT_MESSAGES = {
    "success": "A login attempt was successful.",
    "password_verified": "Your password was verified. Additional security verification may still be required.",
    "failed": "An unsuccessful login attempt was detected.",
    "locked": "A login attempt was blocked because password login is temporarily locked.",
    "disabled": "A login attempt was blocked because password login is disabled.",
    "inactive": "A login attempt was made on an inactive account.",
}


def send_login_attempt_alert(identity, outcome):
    """
    Send a security alert only to the email saved on the known account.
    Email failures must never interrupt authentication.
    """
    try:
        recipient = (getattr(identity, "email", "") or "").strip()

        if not recipient:
            return False

        message = LOGIN_ALERT_MESSAGES.get(outcome)
        if not message:
            return False

        username = getattr(identity, "username", "") or "Account"
        attempted_at = timezone.localtime().strftime(
            "%d %B %Y, %I:%M:%S %p %Z"
        )

        subject = "Deepafy Security Alert: Login Attempt"

        body = (
            "Hello,\n\n"
            f"{message}\n\n"
            f"Account: {username}\n"
            f"Time: {attempted_at}\n\n"
            "If this was not you, please secure your account "
            "and change your password.\n\n"
            "This is an automated security notification from Deepafy.\n"
            "Your password is never included in these emails."
        )

        return bool(send_mail(
            subject=subject,
            message=body,
            from_email=(
                settings.DEFAULT_FROM_EMAIL
                or settings.EMAIL_HOST_USER
            ),
            recipient_list=[recipient],
            fail_silently=False,
        ))

    except Exception:
        logger.exception(
            "Unable to send login security alert for identity ID %s.",
            getattr(identity, "pk", "unknown"),
        )
        return False
