import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


async def send_magic_link(to_email: str, full_name: str, token: str, attempt_title: str) -> bool:
    """Send witness invitation email with magic link."""
    magic_url = f"{settings.FRONTEND_URL}/witness/{token}"

    if not settings.SENDGRID_API_KEY:
        logger.info("SendGrid not configured. Magic link: %s", magic_url)
        return True

    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=settings.EMAIL_FROM,
            to_emails=to_email,
            subject=f"You've been invited to witness a GWR attempt: {attempt_title}",
            html_content=_magic_link_html(full_name, attempt_title, magic_url),
        )
        response = sg.send(message)
        return response.status_code in (200, 202)
    except Exception as e:
        logger.error("Failed to send magic link email: %s", e)
        return False


async def send_notification_email(to_email: str, subject: str, body: str) -> bool:
    if not settings.SENDGRID_API_KEY:
        logger.info("Email (no SendGrid): %s → %s", to_email, subject)
        return True
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail

        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=settings.EMAIL_FROM,
            to_emails=to_email,
            subject=subject,
            html_content=f"<p>{body}</p>",
        )
        response = sg.send(message)
        return response.status_code in (200, 202)
    except Exception as e:
        logger.error("Failed to send email: %s", e)
        return False


def _magic_link_html(full_name: str, attempt_title: str, url: str) -> str:
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2>GWR Witness Invitation</h2>
      <p>Dear {full_name},</p>
      <p>You have been invited to witness the Guinness World Records attempt:</p>
      <p><strong>{attempt_title}</strong></p>
      <p>Please click the button below to access your witness portal and complete your statement:</p>
      <a href="{url}" style="background:#e31837;color:#fff;padding:12px 24px;text-decoration:none;border-radius:4px;display:inline-block;margin:16px 0;">
        Open Witness Portal
      </a>
      <p>This link expires in {72} hours.</p>
      <p>If you did not expect this email, please ignore it.</p>
    </div>
    """
