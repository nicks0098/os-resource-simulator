"""Activity logging. Format: timestamp|LEVEL|module|message  (parsed by scripts/log_report.sh)."""
import logging
import os

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "activity.log")
_configured = False


def get_logger(name: str = "osim") -> logging.Logger:
    global _configured
    logger = logging.getLogger("osim")
    if not _configured:
        os.makedirs(LOG_DIR, exist_ok=True)
        handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s|%(levelname)s|%(module)s|%(message)s"))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        _configured = True
    return logger if name == "osim" else logger.getChild(name)
