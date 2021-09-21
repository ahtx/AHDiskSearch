from imageai.Detection import ObjectDetection
import os
import sqlite3
from time import perf_counter
from sqlite3 import Error
import pandas as pd

db_file = ".\\filesystem.db"

def create_table(conn):
    
    sql_create_file_table = """CREATE TABLE image_objects (
                                filename      TEXT     PRIMARY KEY,
                                objects       TEXT,
                                probabilities TEXT
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

def entry_exists(conn,v1):
    sql = ''' SELECT filename FROM image_objects WHERE filename = ?'''
    cur = conn.cursor()
    cur.execute(sql, (v1,))
    rows = cur.fetchall()
    if len(rows) == 0:
        return False
    else:
        return True

def insert_entry(conn,v1,v2,v3):
    sql = ''' INSERT INTO image_objects(filename,objects,probabilities)
              VALUES(?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, (v1,v2,v3))
    conn.commit()

print("Starting object recognition process...")
t1_start = perf_counter() 

conn = create_connection(db_file)

if conn is not None:
    create_table(conn)
else:
    print("Error: can't create the image_objects table")
    exit()


execution_path = os.getcwd()

detector = ObjectDetection()
detector.setModelTypeAsRetinaNet()
detector.setModelPath(os.path.join(execution_path, "resnet50_coco_best_v2.1.0.h5"))
detector.loadModel()
count = 1

qu = """SELECT filename FROM files WHERE filename LIKE '%.jpg' """

try: 
    df = pd.read_sql_query(f"{qu}", conn)
except:
    print("SQL Error")

for index, row in df.iterrows():
    filename = row['filename']
    if(not entry_exists(conn,filename)):
        try:
            xyz, detections = detector.detectObjectsFromImage(
                                        input_image=filename, 
                                        output_type="array")
            #output_image_path=os.path.join(execution_path , "imagenew.jpg"))
            print(f"{count} Processing {filename}")
            count = count + 1
            objects = []
            probabilities = []
            for eachObject in detections:
                objects.append(eachObject["name"])
                probabilities.append(eachObject["percentage_probability"])
            insert_entry(conn,filename,str(objects),str(probabilities))
        except:
            print(f"Exception occurred with {filename}")
    else:
        print(f"{filename} has already been catalogued")
        
t1_stop = perf_counter()
print("Time elapsed {} seconds".format(t1_stop-t1_start))