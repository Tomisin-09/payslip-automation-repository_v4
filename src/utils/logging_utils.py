from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional


class _StreamToLogger:
    """
    File-like object that redirects writes to a logger.
    Captures print() and stderr tracebacks from some libs.
    """

    def __init__(self, logger: logging.Logger, level: int):
        self.logger = logger
        self.level = level
        self._buffer = ""

    def write(self, message: str) -> None:
        if not message:
            return
        self._buffer += message
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip()
            if line:
                self.logger.log(self.level, line)

    def flush(self) -> None:
        if self._buffer.strip():
            self.logger.log(self.level, self._buffer.strip())
        self._buffer = ""


def configure_logging(
    log_file_path: Path,
    level: str = "INFO",
    *,
    redirect_std_streams: bool = True,
    capture_uncaught_exceptions: bool = True,
) -> logging.Logger:
    """Configure console + file logging for the entire process."""
    log_file_path = log_file_path.resolve()
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(getattr(logging, (level or "INFO").upper(), logging.INFO))

    # Clear existing handlers to avoid duplicate lines on repeated runs
    root.handlers.clear()

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler (explicit stream)
    sh = logging.StreamHandler(stream=sys.__stdout__)
    sh.setLevel(root.level)
    sh.setFormatter(fmt)

    # File handler
    fh = logging.FileHandler(str(log_file_path), encoding="utf-8")
    fh.setLevel(root.level)
    fh.setFormatter(fmt)

    root.addHandler(sh)
    root.addHandler(fh)

    if capture_uncaught_exceptions:
        def _handle_uncaught(exc_type, exc_value, exc_traceback):
            logging.getLogger("uncaught").critical(
                "Uncaught exception",
                exc_info=(exc_type, exc_value, exc_traceback),
            )
        sys.excepthook = _handle_uncaught

    if redirect_std_streams:
        # Redirect print() and raw stderr writes into logging
        sys.stdout = _StreamToLogger(logging.getLogger("stdout"), logging.INFO)  # type: ignore
        sys.stderr = _StreamToLogger(logging.getLogger("stderr"), logging.ERROR)  # type: ignore

    return root
