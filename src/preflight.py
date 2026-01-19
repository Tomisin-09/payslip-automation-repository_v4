from __future__ import annotations

import platform
import sys
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


def run_preflight(settings: Dict[str, Any], project_root: Path) -> None:
    # Python version
    if sys.version_info < (3, 10):
        logger.error(
            f"Python 3.10+ is required. Detected: {sys.version.split()[0]}"
        )
        raise RuntimeError

    # Core paths
    data_cfg = settings.get("data", {})
    branding_cfg = settings.get("branding", {})

    data_source_xlsx = project_root / data_cfg.get("data_source_xlsx", "")
    if str(data_source_xlsx).strip():
        try:
            data_source_xlsx.exists()
                    
        except FileNotFoundError:
            logging.error(
                f"Data source Excel file not found: {data_source_xlsx}\n"
                    "Update config/data_source_xlsx or add the file."
                )
            raise


    # Email capability warning
    email_cfg = settings.get("email", {})
    email_enabled = bool(email_cfg.get("enabled", False))
    if email_enabled and platform.system() != "Windows":
        logger.warning(
            "WARNING: Email sending is enabled in config, but Outlook automation only works on Windows.\n"
            "This run will generate PDFs, but the email step will fail unless you run on Windows with Outlook Desktop + pywin32."
        )

    # Branding asset presence is validated later with clearer errors
