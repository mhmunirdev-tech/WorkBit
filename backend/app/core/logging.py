import logging
import sys

def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
        format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}')
    logging.getLogger("httpx").setLevel(logging.WARNING)
