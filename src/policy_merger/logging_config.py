from __future__ import annotations

import logging
import logging.handlers
import os
from datetime import datetime


def _default_log_dir() -> str:
    home = os.path.expanduser("~")
    return os.path.join(home, ".policy_merger", "logs")


def configure_logging(log_dir: str | None = None) -> str:
    directory = log_dir or _default_log_dir()
    os.makedirs(directory, exist_ok=True)
    session_id = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    log_path = os.path.join(directory, "app.log")

    root = logging.getLogger()
    if any(isinstance(h, logging.handlers.RotatingFileHandler) for h in root.handlers):
        return log_path

    root.setLevel(logging.INFO)
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)

    # Also log minimal info to console for CLI usage
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    console.setFormatter(fmt)
    root.addHandler(console)

    logging.getLogger(__name__).info("Logging initialized", extra={"session": session_id})
    return log_path


