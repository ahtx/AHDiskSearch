import glob
import os
import sqlite3
from time import perf_counter
from sqlite3 import Error

import psutil


def create_table(conn):
    sql_create_file_table = """CREATE TABLE files (
                                filename     TEXT     PRIMARY KEY,
                                size         BIGINT,
                                creation     DATETIME,
                                modification DATETIME
                            );"""
    try:
        c = conn.cursor()
        c.execute(sql_create_file_table)
    except Error as e:
        print(f"Warning: {e}")


def create_connection():
    db_file = os.path.join(os.getcwd(), "filesystem.db")
    try:
        return sqlite3.connect(db_file)
    except Error as e:
        print(e)


def read_path_config():
    paths = None
    try:
        paths = open("ahsearch.config", "r").readlines()
    except:
        pass
    return paths if paths else [partition.device for partition in psutil.disk_partitions()]


def insert_entry(conn, v1, v2, v3, v4):
    sql = ''' INSERT INTO files(filename,size,creation,modification) VALUES(?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, (v1, v2, v3, v4))
    conn.commit()


def save_paths(path, conn):
    print(f"Now indexing {path}")
    for filename in glob.iglob(os.path.join(path, "**/*.*"), recursive=True):
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
            except:
                print(f"Warning: couldn't add entry for {filename}")
        except:
            print("Warning: issue w filename")


def start():
    print("Starting indexing process...")
    try:
        paths = read_path_config()
        conn = create_connection()
        assert conn, 'No database'
        create_table(conn)
        for path in paths:
            path = path.strip("\n")
            save_paths(path, conn)
    except Exception as error:
        print('Error =>> ', error.args[0])


if __name__ == '__main__':
    t1_start = perf_counter()
    start()
    t1_stop = perf_counter()
    print("Time elapsed {} seconds".format(t1_stop - t1_start))
