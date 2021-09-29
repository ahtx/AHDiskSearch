import glob
import os
import sys
from time import perf_counter
from sqlite3 import Error, IntegrityError

import win32api
import win32event
import winerror

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist.shared import BASE_DIR, create_connection, LOGGER

# Disallowing Multiple Instance
mutex = win32event.CreateMutex(None, 1, 'mutex_AHDiskIndexer')
if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    mutex = None
    LOGGER.warning("AHDiskIndexer is already running.")
    sys.exit(0)


def create_table(conn):
    query = "CREATE TABLE files (filename TEXT PRIMARY KEY, size BIGINT, creation DATETIME, modification DATETIME);"
    try:
        c = conn.cursor()
        c.execute(query)
    except Error as e:
        LOGGER.warning(e)


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
    LOGGER.warning(f"Now indexing {path}")
    path = glob.escape(path)
    files = set(glob.iglob(os.path.join(path, "**/*.*"), recursive=True))
    total = len(files)
    for index, filename in enumerate(files):
        LOGGER.warning(f"Indexing {index + 1} out of {total}")
        try:
            filename = filename.replace("/", os.path.sep).replace("\\", os.path.sep)
            filestat = os.stat(filename)
            filesize = filestat.st_size
            filecreation = filestat.st_ctime
            filemod = filestat.st_mtime
            try:
                insert_entry(conn, filename, filesize, filecreation, filemod)
            except IntegrityError as error:
                continue
            except Exception as error:
                LOGGER.error(error)
        except Exception as error:
            LOGGER.error(error)


def start():
    LOGGER.warning("Starting indexing process...")
    try:
        paths = read_path_config()
        conn = create_connection()
        assert conn, 'No index database found'
        create_table(conn)
        for path in paths:
            path = path.strip("\n")
            save_paths(path, conn)
    except Exception as error:
        LOGGER.warning(error)


if __name__ == '__main__':
    t1_start = perf_counter()
    start()
    t1_stop = perf_counter()
    LOGGER.warning("Time elapsed {} seconds".format(t1_stop - t1_start))
