# https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output

from cfg import *
import logging
import os

class CustomFormatter(logging.Formatter):

    green = "\x1b[32m"
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    # format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    format = '%(levelname)-8s | %(message)-80s | %(funcName)s:%(lineno)s'

    FORMATS = {
        logging.DEBUG:    logging.Formatter(green + format + reset),
        logging.INFO:     logging.Formatter(grey + format + reset),
        logging.WARNING:  logging.Formatter(yellow + format + reset),
        logging.ERROR:    logging.Formatter(red + format + reset),
        logging.CRITICAL: logging.Formatter(bold_red + format + reset)
    }

    def format(self, record):
        formatter = self.FORMATS.get(record.levelno)
        return formatter.format(record)

def init():
    lvl = logging.getLevelName(ARGS[PARAM_LOG].upper())
    logger = logging.getLogger()
    logger.setLevel(lvl)

    ch = logging.StreamHandler()
    ch.setLevel(lvl)
    ch.setFormatter(CustomFormatter())
    logger.addHandler(ch)
    os.system('color')