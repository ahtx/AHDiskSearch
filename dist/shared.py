import json
import logging
import os
import sqlite3
from collections import namedtuple
from functools import reduce

LOGGER = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATE_TIME_FORMAT = "%m/%d/%Y, %H:%M"
Stats = namedtuple('Stats', ['count', 'size', 'datetime'])
c_handler = logging.StreamHandler()
DIST_DIR = os.path.join(BASE_DIR, 'ttkbootstrap')
if not os.path.exists(DIST_DIR):
    os.makedirs(DIST_DIR)
f_handler = logging.FileHandler(os.path.join(DIST_DIR, 'error.log'))
c_handler.setLevel(logging.WARNING)
f_handler.setLevel(logging.ERROR)
log_format = logging.Formatter('%(asctime)s-%(levelname)s - %(message)s', datefmt=DATE_TIME_FORMAT)
c_handler.setFormatter(log_format)
f_handler.setFormatter(log_format)
LOGGER.addHandler(c_handler)
LOGGER.addHandler(f_handler)

TABLES = ('files', 'voices', 'image_objects')

def get_sub_string(data: list, query_append, prefix='filename = ', like_query=False):
    try:
        assert data, 'Not found'
        result = reduce(lambda x, y: x.replace("'", "''") + f"{query_append}" + y.replace("'", "''"), data)
        return prefix + f'{query_append}'.join(
            f"'%{word}%'" if like_query else f"'{word}'" for word in result.split(f'{query_append}'))
    except Exception as error:
        LOGGER.warning(error)
        return ""


def read_path_config():
    config_file = os.path.join(DIST_DIR, 'ahsearch.config')
    with open(config_file) as open_file:
        try:
            data = json.load(open_file)
        except json.decoder.JSONDecodeError:
            data = {}
    return data


def execute_queries(conn, query):
    try:
        conn.cursor().execute(query)
    except sqlite3.OperationalError as err:
        LOGGER.warning(err)
    except Exception as err:
        LOGGER.error(err)


def tables():
    files = "CREATE TABLE files (filename TEXT PRIMARY KEY, size BIGINT, creation DATETIME, modification DATETIME);"
    image_objects = "CREATE TABLE image_objects (filename TEXT PRIMARY KEY, objects TEXT, probabilities TEXT);"
    voices = "CREATE TABLE voices (filename TEXT PRIMARY KEY, words TEXT);"
    return files, image_objects, voices


def convert_bytes(size):
    kb = 1024
    mbs = 1024 * 1024
    gbs = 1024 * 1024 * 1024
    if size < kb:
        return f"{size} Bytes"
    elif kb < size < mbs:
        return f"{round(size / kb, 2)} KB"
    elif mbs < size < gbs:
        return f"{round(size / mbs, 2)} MB"
    else:
        return f"{round(size / gbs, 2)} GB"


def kb_to_mbs(number):
    return round(number / (1024 * 1024), 2)


def create_connection(create_tables=True):
    try:
        db_file = os.path.join(DIST_DIR, 'filesystem.db')
        conn = sqlite3.connect(db_file)
        if create_tables:
            for query in tables():
                execute_queries(conn, query)
        return conn
    except Exception as err:
        LOGGER.error(err)


def remove_entry(filename):
    conn = create_connection(create_tables=False)
    for table in TABLES:
        sql = f"DELETE FROM {table} WHERE filename=?"
        conn.cursor().execute(sql, (filename,))
        conn.commit()
    conn.close()
