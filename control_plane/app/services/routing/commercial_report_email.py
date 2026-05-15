from __future__ import annotations

import asyncio
import logging
import re
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Any

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}$", re.IGNORECASE)
SUSPICIOUS_VALUE_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_\-]{8,}\b", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._\-+/=]{8,}\b", re.IGNORECASE),
    re.compile(r"\b(?:authorization|api[_-]?key|secret|token|password)\b\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
    re.compile(r"\b(?:OPENAI|ANTHROPIC|DEEPSEEK|OPENROUTER)_[A-Z_]*KEY\b", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9+/=_\-]{128,}\b"),
]
PROHIBITED_KEYS = {
    "authorization",
    "api_key",
    "api_keys",
    "secret",
    "secrets",
    "password",
    "token",
    "tokens",
    "prompt",
    "prompts",
    "response",
    "responses",
    "raw_payload",
    "payload",
    "provider_secret",
    "provider_secrets",
}
ALLOWED_ATTACHMENT_EXTENSIONS = {".json", ".csv", ".html", ".pdf"}
MAX_ATTACHMENT_BYTES = 2 * 1024 * 1024


class CommercialReportEmailError(Exception):
    pass


class AllowlistError(CommercialReportEmailError):
    pass


class SecurityScanError(CommercialReportEmailError):
    pass


class SMTPAuthFailure(CommercialReportEmailError):
    pass


class SMTPTLSFailure(CommercialReportEmailError):
    pass


@dataclass
class EmailAttachment:
    filename: str
    content: bytes
    mime_type: str


def _settings(settings: Settings | None = None) -> Settings:
    return settings or get_settings()


def _mask_smtp_host(host: str | None) -> str | None:
    if not host:
        return None
    parts = host.split(".")
    if not parts:
        return "***"
    head = parts[0]
    masked_head = head[:1] + "***" if head else "***"
    return ".".join([masked_head, *parts[1:]])


def _sanitize_error_message(message: str | None) -> str | None:
    if not message:
        return None
    sanitized = message
    for pattern in SUSPICIOUS_VALUE_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized[:500]


def _scan_scalar(key: str, value: Any) -> Any:
    lowered = key.lower()
    if lowered in PROHIBITED_KEYS:
        raise SecurityScanError(f"blocked_by_security: prohibited field '{key}' in email payload")
    if isinstance(value, str):
        for pattern in SUSPICIOUS_VALUE_PATTERNS:
            if pattern.search(value):
                raise SecurityScanError(f"blocked_by_security: sensitive value detected in field '{key}'")
    return value


def sanitize_email_payload(payload: Any) -> Any:
    def _walk(node: Any, parent_key: str = "value") -> Any:
        if isinstance(node, dict):
            return {str(key): _walk(_scan_scalar(str(key), value), str(key)) for key, value in node.items()}
        if isinstance(node, list):
            return [_walk(item, parent_key) for item in node]
        return _scan_scalar(parent_key, node)

    return _walk(payload)


def _parse_allowlist(settings: Settings | None = None) -> set[str]:
    raw = _settings(settings).commercial_report_email_allowlist
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def validate_recipient_allowlist(
    recipients: list[str],
    *,
    settings: Settings | None = None,
) -> list[str]:
    cfg = _settings(settings)
    normalized = [recipient.strip().lower() for recipient in recipients if recipient and recipient.strip()]
    if not normalized:
        raise AllowlistError("blocked_by_allowlist: at least one recipient is required")
    if len(normalized) > cfg.commercial_report_email_max_recipients:
        raise AllowlistError(
            f"blocked_by_allowlist: max recipients is {cfg.commercial_report_email_max_recipients}"
        )
    allowlist = _parse_allowlist(cfg)
    if not allowlist:
        raise AllowlistError("blocked_by_allowlist: COMMERCIAL_REPORT_EMAIL_ALLOWLIST is empty")
    invalid = [recipient for recipient in normalized if not EMAIL_RE.match(recipient)]
    if invalid:
        raise AllowlistError(f"blocked_by_allowlist: invalid email recipient '{invalid[0]}'")
    blocked = [recipient for recipient in normalized if recipient not in allowlist]
    if blocked:
        raise AllowlistError(f"blocked_by_allowlist: recipient '{blocked[0]}' is not allowlisted")
    return normalized


def validate_basic_recipients(
    recipients: list[str],
    *,
    settings: Settings | None = None,
) -> list[str]:
    cfg = _settings(settings)
    normalized = [recipient.strip().lower() for recipient in recipients if recipient and recipient.strip()]
    if not normalized:
        raise AllowlistError("blocked_by_allowlist: at least one recipient is required")
    if len(normalized) > cfg.commercial_report_email_max_recipients:
        raise AllowlistError(
            f"blocked_by_allowlist: max recipients is {cfg.commercial_report_email_max_recipients}"
        )
    invalid = [recipient for recipient in normalized if not EMAIL_RE.match(recipient)]
    if invalid:
        raise AllowlistError(f"blocked_by_allowlist: invalid email recipient '{invalid[0]}'")
    return normalized


def validate_attachment_safety(filename: str, content: bytes, mime_type: str) -> None:
    lowered = filename.lower()
    if not any(lowered.endswith(ext) for ext in ALLOWED_ATTACHMENT_EXTENSIONS):
        raise SecurityScanError(f"blocked_by_security: attachment '{filename}' has unsupported extension")
    if len(content) > MAX_ATTACHMENT_BYTES:
        raise SecurityScanError(f"blocked_by_security: attachment '{filename}' exceeds safety size limit")
    if mime_type.startswith("text/") or lowered.endswith((".json", ".csv", ".html")):
        try:
            sanitize_email_payload(content.decode("utf-8", errors="ignore"))
        except SecurityScanError as exc:
            raise SecurityScanError(f"blocked_by_security: attachment '{filename}' failed scan") from exc


def build_email_message(
    *,
    subject: str,
    recipients: list[str],
    body_text: str,
    attachments: list[EmailAttachment],
    settings: Settings | None = None,
) -> EmailMessage:
    cfg = _settings(settings)
    if not cfg.commercial_report_smtp_from.strip():
        raise CommercialReportEmailError("smtp_from is required for SMTP delivery")
    sanitize_email_payload({"subject": subject, "body_text": body_text, "recipients": recipients})
    for attachment in attachments:
        validate_attachment_safety(attachment.filename, attachment.content, attachment.mime_type)

    message = EmailMessage()
    message["Subject"] = subject[:255]
    message["From"] = cfg.commercial_report_smtp_from.strip()
    message["To"] = ", ".join(recipients)
    message.set_content(body_text[:20000])

    for attachment in attachments:
        maintype, subtype = attachment.mime_type.split("/", 1)
        message.add_attachment(
            attachment.content,
            maintype=maintype,
            subtype=subtype,
            filename=attachment.filename,
        )
    return message


def send_report_email(
    message: EmailMessage,
    recipients: list[str],
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = _settings(settings)
    timeout = cfg.commercial_report_smtp_timeout_seconds
    host = cfg.commercial_report_smtp_host.strip()
    username = cfg.commercial_report_smtp_username.strip()
    password = cfg.commercial_report_smtp_password

    if not host:
        raise CommercialReportEmailError("smtp_host is required for SMTP delivery")

    context = ssl.create_default_context()
    try:
        if cfg.commercial_report_smtp_use_tls and not cfg.commercial_report_smtp_use_starttls:
            with smtplib.SMTP_SSL(host, cfg.commercial_report_smtp_port, timeout=timeout, context=context) as smtp:
                if username:
                    smtp.login(username, password)
                smtp.send_message(message, to_addrs=recipients)
        else:
            with smtplib.SMTP(host, cfg.commercial_report_smtp_port, timeout=timeout) as smtp:
                smtp.ehlo()
                if cfg.commercial_report_smtp_use_starttls:
                    smtp.starttls(context=context)
                    smtp.ehlo()
                if username:
                    smtp.login(username, password)
                smtp.send_message(message, to_addrs=recipients)
    except smtplib.SMTPAuthenticationError as exc:
        raise SMTPAuthFailure("auth_failure: SMTP authentication failed") from exc
    except (ssl.SSLError, smtplib.SMTPNotSupportedError) as exc:
        raise SMTPTLSFailure("tls_failure: SMTP TLS negotiation failed") from exc
    except smtplib.SMTPException as exc:
        raise CommercialReportEmailError(_sanitize_error_message(f"smtp_failure: {exc}")) from exc
    except OSError as exc:
        raise CommercialReportEmailError(_sanitize_error_message(f"smtp_network_failure: {exc}")) from exc

    logger.info(
        "commercial report email sent",
        extra={
            "extra_data": {
                "smtp_host": _mask_smtp_host(host),
                "recipient_count": len(recipients),
            }
        },
    )
    return {
        "status": "sent",
        "smtp_host": _mask_smtp_host(host),
    }


def send_report_email_dry_run(
    *,
    subject: str,
    recipients: list[str],
    attachments: list[EmailAttachment],
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = _settings(settings)
    if _parse_allowlist(cfg):
        validate_recipient_allowlist(recipients, settings=cfg)
    else:
        validate_basic_recipients(recipients, settings=cfg)
    sanitize_email_payload(
        {
            "subject": subject,
            "recipients": recipients,
            "attachment_names": [item.filename for item in attachments],
        }
    )
    for attachment in attachments:
        validate_attachment_safety(attachment.filename, attachment.content, attachment.mime_type)
    logger.info(
        "commercial report email dry run",
        extra={
            "extra_data": {
                "smtp_host": _mask_smtp_host(cfg.commercial_report_smtp_host),
                "recipient_count": len(recipients),
                "attachment_count": len(attachments),
            }
        },
    )
    return {
        "status": "dry_run",
        "smtp_host": _mask_smtp_host(cfg.commercial_report_smtp_host),
    }


async def retry_send_with_backoff(
    send_callable,
    *,
    retry_count: int,
    backoff_seconds: int,
) -> tuple[dict[str, Any], int]:
    retries = 0
    for attempt in range(retry_count + 1):
        try:
            result = send_callable()
            return result, retries
        except (SecurityScanError, AllowlistError, SMTPAuthFailure, SMTPTLSFailure):
            raise
        except CommercialReportEmailError:
            if attempt >= retry_count:
                raise
            retries += 1
            await asyncio.sleep(max(1, backoff_seconds) * (2 ** (attempt)))
    raise CommercialReportEmailError("smtp_failure: retries exhausted")


__all__ = [
    "AllowlistError",
    "CommercialReportEmailError",
    "EmailAttachment",
    "SMTPAuthFailure",
    "SMTPTLSFailure",
    "SecurityScanError",
    "build_email_message",
    "retry_send_with_backoff",
    "sanitize_email_payload",
    "send_report_email",
    "send_report_email_dry_run",
    "validate_basic_recipients",
    "validate_attachment_safety",
    "validate_recipient_allowlist",
]
