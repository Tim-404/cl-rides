"""
"""

import logging


logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(module)s[%(lineno)d] - %(message)s",
    level=logging.DEBUG
)


def main():
    """
    """
    logging.debug("Hello World!")
