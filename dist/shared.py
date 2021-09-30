import logging
import os
import sqlite3
from collections import namedtuple

LOGGER = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGGER_TIME_FORMAT = '%b-%d-%y %H:%M:%S'
Stats = namedtuple('Stats', ['count', 'size', 'datetime'])
c_handler = logging.StreamHandler()
f_handler = logging.FileHandler(os.path.join(BASE_DIR, 'dist', 'error.log'))
c_handler.setLevel(logging.WARNING)
f_handler.setLevel(logging.ERROR)
log_format = logging.Formatter('%(asctime)s-%(levelname)s - %(message)s', datefmt=LOGGER_TIME_FORMAT)
c_handler.setFormatter(log_format)
f_handler.setFormatter(log_format)
LOGGER.addHandler(c_handler)
LOGGER.addHandler(f_handler)


def create_connection():
    try:
        db_file = os.path.join(BASE_DIR, 'dist', 'filesystem.db')
        print(db_file)
        return sqlite3.connect(db_file)
    except Exception as e:
        print(e)
