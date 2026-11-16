import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path


def setup():
    logger = logging.getLogger('contador-carpetas')
    logger.setLevel(logging.WARNING)
    if not logger.handlers:
        try:
            directory = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'contador-carpetas'
            directory.mkdir(parents=True, exist_ok=True)
            handler = RotatingFileHandler(directory / 'errors.log', maxBytes=1_000_000, backupCount=2, encoding='utf-8')
        except OSError:
            handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logger.addHandler(handler)
    return logger
