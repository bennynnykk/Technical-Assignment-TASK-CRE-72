import logging
import sys


def setup_logging(level=logging.INFO):
    """Configure root logging once; safe to call repeatedly."""
    root = logging.getLogger()

    if root.handlers:
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root.addHandler(handler)
    root.setLevel(level)
