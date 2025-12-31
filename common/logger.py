import logging


def get_logger(name: str):
    """Utility to fetch a logger configured for the given module name."""
    return logging.getLogger(name)
