import logging
import os
import sys
from config import Config

def setup_logger(name="RazgonBot"):
    # Ensure log directory exists
    if not os.path.exists(Config.LOG_DIR):
        os.makedirs(Config.LOG_DIR)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # File Handler
    log_file = os.path.join(Config.LOG_DIR, "bot.log")
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

logger = setup_logger()
