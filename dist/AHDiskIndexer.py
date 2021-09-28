import glob
import logging
import os
import sys
from time import perf_counter
from sqlite3 import Error

import win32api
import win32event
import winerror
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist.shared import BASE_DIR, create_connection, LOGGER_TIME_FORMAT

log_file = os.path.join(BASE_DIR, 'dist', 'disk_indexer.log')
logging.basicConfig(
    filename=log_file,
    filemode='w',
    format='%(asctime)s-%(levelname)s - %(message)s',
    datefmt=LOGGER_TIME_FORMAT
)

# Disallowing Multiple Instance
mutex = win32event.CreateMutex(None, 1, 'mutex_AHDiskIndexer')
if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    mutex = None
    logging.info("AHDiskIndexer already running.")
    sys.exit(0)


def create_table(conn):
    query = "CREATE TABLE files (filename TEXT PRIMARY KEY, size BIGINT, creation DATETIME, modification DATETIME);"
    try:
        c = conn.cursor()
        c.execute(query)
    except Error as e:
        logging.warning(e)


def read_path_config():
    paths = None
    try:
        config_file = os.path.join(BASE_DIR, 'dist', 'ahsearch.config')
        with open(config_file, "r") as c_file:
            paths = c_file.readlines()
    except Exception as error:
        pass
    return paths if paths else []


def insert_entry(conn, v1, v2, v3, v4):
    sql = "INSERT INTO files(filename,size,creation,modification) VALUES(?,?,?,?) "
    cur = conn.cursor()
    cur.execute(sql, (v1, v2, v3, v4))
    conn.commit()


def save_paths(path, conn):
    logging.info(f"Now indexing {path}")
    for filename in glob.iglob(os.path.join(glob.escape(path), "**/*.*"), recursive=True):
        if os.path.isdir(filename):
            continue
        try:
            filename = filename.replace("/", os.path.sep).replace("\\", os.path.sep)
            filestat = os.stat(filename)
            filesize = filestat.st_size
            filecreation = filestat.st_ctime
            filemod = filestat.st_mtime
            # findex.write(f"{filename},{filesize},{filecreation},{filemod}\n")
            try:
                insert_entry(conn, filename, filesize, filecreation, filemod)
            except Exception as error:
                logging.warning(error)
        except Exception as error:
            logging.warning(error)


def start():
    logging.info("Starting indexing process...")
    try:
        paths = read_path_config()
        conn = create_connection()
        assert conn, 'No database'
        create_table(conn)
        for path in paths:
            path = path.strip("\n")
            save_paths(path, conn)
    except Exception as error:
        logging.warning(error)


if __name__ == '__main__':
    t1_start = perf_counter()
    start()
    t1_stop = perf_counter()
    logging.info("Time elapsed {} seconds".format(t1_stop - t1_start))
