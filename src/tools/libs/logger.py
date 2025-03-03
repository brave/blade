#!/usr/bin/python3

# Note:   Logging functionality in blade
# Author: Ralph Ankele (rankele@brave.com)
# Date:   06/02/2025

import logging
import sys


def set_logging_level(level="warning"):
    """
    Updates the log level of the logger.
    """

    match level:
        case "debug": logger.setLevel(logging.DEBUG)
        case "info": logger.setLevel(logging.INFO)
        case "warning": logger.setLevel(logging.WARNING)
        case "error": logger.setLevel(logging.ERROR)
        case "critical": logger.setLevel(logging.CRITICAL)
        case _: pass


def add_file_handler(log_file, level=logging.INFO):
    """
    Adds or updates the file handler for the logger.
    """

    # Remove existing file handlers if any
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)
    
    # Create new file handler
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setLevel(level)
    file_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s",
                                    datefmt="%Y/%m/%d %I:%M:%S %p")
    file_handler.setFormatter(file_format)
    
    logger.addHandler(file_handler)
    logger.info(f"Logging to file at: {log_file}")


def setup_logger():
    """
    Sets up a logger to log output to the stdout
    """

    logger = logging.getLogger('blade')
    
    if logger.hasHandlers():  # Prevent adding duplicate handlers
        return logger

    logger.setLevel(logging.INFO)

    # Console handler (logs to stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter("%(message)s")
    console_handler.setFormatter(console_format)

    logger.addHandler(console_handler)

    return logger


# create global logger
logger = setup_logger()
