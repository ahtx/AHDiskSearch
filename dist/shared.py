import logging
import os
import sqlite3
from collections import namedtuple
from functools import reduce

LOGGER = logging.getLogger(__name__)
BASE_DIR = os.getcwd()
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

DATE_TIME_FORMAT = "%m/%d/%Y, %H:%M:%S"


def get_sub_string(data: list, query_append, prefix='filename = ', like_query=False):
    try:
        assert data, 'Not found'
        result = reduce(lambda x, y: x.replace("'", "''") + f"{query_append}" + y.replace("'", "''"), data)
        return prefix + f'{query_append}'.join(
            f"'%{word}%'" if like_query else f"'{word}'" for word in result.split(f'{query_append}'))
    except Exception as error:
        LOGGER.warning(error)
        return ""


def create_connection():
    try:
        db_file = os.path.join(BASE_DIR, 'dist', 'filesystem.db')
        return sqlite3.connect(db_file)
    except Exception as e:
        print(e)
