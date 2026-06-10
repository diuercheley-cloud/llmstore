import html
import json
import logging
import re
import smtplib
import urllib.error
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from app.core.config import get_settings
from app.models.agents.agent_notifications import NotificationPreference
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("email_provider")


def sanitize_template(content: str) -> str:
    """Sanitizes email template content to prevent code injection/XSS."""
    # Remove script tags and their content
    clean = re.sub(r"<script.*?>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
    # Remove iframe tags
    clean = re.sub(r"<iframe.*?>.*?</iframe>", "", clean, flags=re.DOTALL | re.IGNORECASE)
    # Remove javascript: links
    clean = re.sub(r"href\s*=\s*[\"']\s*javascript:.*?[\"']", "", clean, flags=re.IGNORECASE)
    # Strip on* event handlers (e.g. onload, onclick)
    clean = re.sub(r"\son[a-zA-Z]+\s*=\s*[\"'].*?[\"']", "", clean, flags=re.IGNORECASE)
    return clean


class EmailProviderService:
    # A class-level storage for mock emails, useful for tests
    sent_mock_emails = []

    @classmethod
    def clear_mock_emails(cls):
        cls.sent_mock_emails.clear()

    @classmethod
    async def send_email(
        cls,
        db: AsyncSession,
        tenant_id: str,
        recipient: str,
        title: str,
        body: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Sends an email notification if feature flags allow and user preferences are met."""
        settings = get_settings()

        # 1. Check feature flag
        if not settings.agent_email_notifications_enabled:
            raise ValueError("Email notifications are disabled by feature flag.")

        # 2. Check unsubscribe / user preferences
        # Check by user_id
        if user_id:
            stmt = select(NotificationPreference).where(
                NotificationPreference.tenant_id == tenant_id,
                NotificationPreference.user_id == user_id
            )
            res = await db.execute(stmt)
            pref = res.scalar_one_or_none()
            if pref and not pref.email_enabled:
                raise ValueError(f"User {user_id} has disabled email notifications.")

        # Check by recipient email address (in case user_id is the recipient or pref is registered under recipient)
        stmt_rec = select(NotificationPreference).where(
            NotificationPreference.tenant_id == tenant_id,
            NotificationPreference.user_id == recipient
        )
        res_rec = await db.execute(stmt_rec)
        pref_rec = res_rec.scalar_one_or_none()
        if pref_rec and not pref_rec.email_enabled:
            raise ValueError(f"Recipient {recipient} has disabled email notifications.")

        # 3. Sanitize content
        sanitized_title = html.escape(title)
        sanitized_body = sanitize_template(body)

        provider = settings.email_provider.lower()
        if provider == "mock":
            cls.sent_mock_emails.append({
                "tenant_id": tenant_id,
                "recipient": recipient,
                "title": sanitized_title,
                "body": sanitized_body,
                "user_id": user_id
            })
            logger.info(f"[Mock Email] Sent to {recipient}: {sanitized_title}")
            return {"status": "sent", "provider": "mock", "recipient": recipient}

        elif provider == "smtp":
            return cls._send_smtp(recipient, sanitized_title, sanitized_body)

        elif provider == "sendgrid":
            return cls._send_sendgrid(recipient, sanitized_title, sanitized_body)

        else:
            raise ValueError(f"Unknown email provider configured: {provider}")

    @classmethod
    def _send_smtp(cls, recipient: str, title: str, body: str) -> Dict[str, Any]:
        settings = get_settings()
        if not settings.smtp_host:
            raise ValueError("SMTP host is not configured.")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = title
        msg["From"] = settings.smtp_username or "no-reply@agentplatform.com"
        msg["To"] = recipient

        # Append opt-out footer
        footer = "\n\n---\nTo unsubscribe from these emails, update your notification preferences."
        part_text = MIMEText(body + footer, "plain")
        msg.attach(part_text)

        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
                if settings.smtp_username and settings.smtp_password:
                    server.starttls()
                    server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(msg["From"], [recipient], msg.as_string())
            return {"status": "sent", "provider": "smtp", "recipient": recipient}
        except Exception as e:
            logger.error(f"SMTP send failed: {e}")
            raise RuntimeError(f"SMTP email sending failed: {e}")

    @classmethod
    def _send_sendgrid(cls, recipient: str, title: str, body: str) -> Dict[str, Any]:
        settings = get_settings()
        if not settings.sendgrid_api_key:
            raise ValueError("SendGrid API Key is not configured.")

        url = "https://api.sendgrid.com/v3/mail/send"
        sender = "no-reply@agentplatform.com"
        
        # Add unsubscribe/opt-out text
        footer = "<br/><br/><hr/><p style='font-size: 11px; color: #666;'>To unsubscribe, update your preferences in the app.</p>"
        payload = {
            "personalizations": [{"to": [{"email": recipient}]}],
            "from": {"email": sender},
            "subject": title,
            "content": [{"type": "text/html", "value": body + footer}]
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {settings.sendgrid_api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 202):
                    return {"status": "sent", "provider": "sendgrid", "recipient": recipient}
                else:
                    raise RuntimeError(f"SendGrid returned unexpected status: {response.status}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            logger.error(f"SendGrid HTTP error: {err_body}")
            raise RuntimeError(f"SendGrid API call failed: {e.code} - {err_body}")
        except Exception as e:
            logger.error(f"SendGrid call failed: {e}")
            raise RuntimeError(f"SendGrid call failed: {e}")
