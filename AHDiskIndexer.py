import os
import sqlite3
from time import perf_counter
from sqlite3 import Error

db_file = ".\\filesystem.db"

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


def create_connection(db):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn

def read_path_config():
    paths = ['c:\\']

    try:
        paths = open("ahsearch.config","r").readlines()
    except:
        pass

    return paths

def insert_entry(conn,v1,v2,v3,v4):
    sql = ''' INSERT INTO files(filename,size,creation,modification)
              VALUES(?,?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, (v1,v2,v3,v4))
    conn.commit()

print("Starting indexing process...")
t1_start = perf_counter() 
paths = read_path_config()
conn = create_connection(db_file)

if conn is not None:
    create_table(conn)
else:
    print("Error: can't create the file index table")
    exit()


for path in paths:
    path = path.strip("\n")
    print(f"Now indexing {path}")
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    filename = os.path.join(root,f)
                    filename = filename.replace("/",os.path.sep)
                    filename = filename.replace("\\",os.path.sep)
                    filestat = os.stat(filename)
                    filesize = filestat.st_size
                    filecreation = filestat.st_ctime
                    filemod = filestat.st_mtime
                    #findex.write(f"{filename},{filesize},{filecreation},{filemod}\n")
                    try:
                        insert_entry(conn,filename,filesize,filecreation,filemod)
                    except:
                        print(f"Warning: couldn't add entry for {filename}")
                except:
                    print("Warning: issue w filename")
    except:
        print(f"Warning: Invalid path {path}")
        
t1_stop = perf_counter()
print("Time elapsed {} seconds".format(t1_stop-t1_start))
