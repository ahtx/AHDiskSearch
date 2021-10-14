import glob
import os
import sys
from pathlib import Path
from time import perf_counter
from sqlite3 import Error, IntegrityError

import win32api
import win32event
import winerror

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist.shared import create_connection, LOGGER, read_path_config


def create_table(conn):
    query = "CREATE TABLE files (filename TEXT PRIMARY KEY, size BIGINT, creation DATETIME, modification DATETIME);"
    try:
        c = conn.cursor()
        c.execute(query)
    except Error as e:
        LOGGER.warning(e)


def entry_exists(conn, filename, size):
    sql = "SELECT filename FROM files WHERE filename = ? AND size = ? "
    row = conn.cursor().execute(sql, (filename, size)).fetchone()
    return True if row else False


def insert_entry(conn, filename, size, creation, modification):
    args = (filename, size, creation, modification)
    try:
        query = "INSERT INTO files(filename,size,creation,modification) VALUES(?,?,?,?) "
        conn.cursor().execute(query, args)
        conn.commit()
    except IntegrityError:
        if not entry_exists(conn, filename, size):
            LOGGER.warning(f"Updating {filename}")
            query = "UPDATE files SET size = ?, modification = ? WHERE filename = ? "
            conn.cursor().execute(query, (size, modification, filename))
            conn.commit()


def is_excluded(file, excluded):
    in_file = False
    for path in excluded:
        if path in file:
            in_file = True
            break
    return in_file


def save_paths(path, excluded, conn):
    LOGGER.warning(f"Now indexing {path}")
    path = glob.escape(path)
    files = set(glob.iglob(os.path.join(path, "**/*.*"), recursive=True))
    total = len(files)
    for index, filename in enumerate(files):
        LOGGER.warning(f"Indexing {index + 1} out of {total}")
        filename = str(Path(filename).absolute())
        if is_excluded(filename, excluded):
            continue
        try:
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
    t1_start = perf_counter()
    LOGGER.error("Starting indexing process...")
    try:
        data = read_path_config()
        conn = create_connection()
        assert conn, 'No index database found'
        create_table(conn)
        for path in data.get('included', []):
            path = path.strip("\n")
            save_paths(path, data.get('excluded', []), conn)
    except Exception as error:
        LOGGER.warning(error)
    t2_stop = perf_counter()
    LOGGER.error("Time elapsed {} seconds".format(t2_stop - t1_start))


if __name__ == '__main__':
    # Disallowing Multiple Instance
    mutex = win32event.CreateMutex(None, 1, 'mutex_AHDiskIndexer')
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        mutex = None
        LOGGER.warning("AHDiskIndexer is already running.")
        sys.exit(0)
    start()
