from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import win32com.client  # type: ignore
    WIN32COM_AVAILABLE = True
except Exception:
    WIN32COM_AVAILABLE = False


@dataclass(frozen=True)
class EmailRequest:
    to: str
    subject: str
    body: str
    attachment_path: Path


def send_or_display_via_outlook(req: EmailRequest, mode: str = "display") -> None:
    """Create an Outlook email per payslip.

    mode:
      - display: opens draft for review
      - send: sends immediately
    """
    if not WIN32COM_AVAILABLE:
        logger.error(
            "Outlook emailing requires Windows + Outlook Desktop + pywin32. "
            "This environment does not support win32com.client."
        )
        raise RuntimeError

    if not req.to:
        logger.error("Missing recipient email address")
        raise ValueError

    app = win32com.client.Dispatch("Outlook.Application")
    mail = app.CreateItem(0)  # 0 = olMailItem
    mail.To = req.to
    mail.Subject = req.subject
    mail.Body = req.body

    attachment_path = req.attachment_path.resolve()
    if not attachment_path.exists():
        logger.error(f"Attachment not found: {attachment_path}")
        raise FileNotFoundError

    mail.Attachments.Add(str(attachment_path))

    mode = (mode or "display").strip().lower()
    if mode == "send":
        logger.info("Sending email to %s", req.to)
        mail.Send()
    else:
        logger.info("Displaying email draft for %s", req.to)
        mail.Display(True)
