import os
import sqlite3
from time import perf_counter
from sqlite3 import Error
import pandas as pd


def create_table(conn):
    query = """CREATE TABLE image_objects (filename TEXT PRIMARY KEY,  objects TEXT, probabilities TEXT);"""
    try:
        conn.cursor().execute(query)
    except Error as e:
        print(f"Warning: {e}")


def create_connection():
    try:
        db_file = os.path.join(os.getcwd(), "filesystem.db")
        return sqlite3.connect(db_file)
    except Error as e:
        print("Line 23 Error ==> ", e.args[0])


def entry_exists(conn, v1):
    sql = ''' SELECT filename FROM image_objects WHERE filename = ?'''
    cursor = conn.cursor()
    cursor.execute(sql, (v1,))
    rows = cursor.fetchall()
    if len(rows) == 0:
        return False
    else:
        return True


def insert_entry(conn, v1, v2, v3):
    sql = ''' INSERT INTO image_objects(filename,objects,probabilities) VALUES(?,?,?) '''
    cur = conn.cursor()
    cur.execute(sql, (v1, v2, v3))
    conn.commit()


def start(conn):
    qu = """SELECT filename FROM files WHERE filename LIKE '%.jpg' """
    try:
        df = pd.read_sql_query(f"{qu}", conn)
        count = 1
        for index, row in df.iterrows():
            filename = row['filename']
            if entry_exists(conn, filename):
                print(f"{filename} has already been catalogued")
                continue
            try:
                xyz, detections = detector.detectObjectsFromImage(
                    input_image=filename,
                    output_type="array")
                # output_image_path=os.path.join(execution_path , "imagenew.jpg"))
                print(f"{count} Processing {filename}")
                count += 1
                objects = []
                probabilities = []
                for eachObject in detections:
                    objects.append(eachObject["name"])
                    probabilities.append(eachObject["percentage_probability"])
                insert_entry(conn, filename, str(objects), str(probabilities))
            except:
                print(f"Exception occurred with {filename}")
    except:
        print("SQL Error")


if __name__ == '__main__':
    print("Starting object recognition process...")
    t1_start = perf_counter()
    conn = create_connection()

    if not conn:
        print("Error: can't create the image_objects table")
        exit()
    create_table(conn)
    execution_path = os.getcwd()
    model_path = os.path.join(execution_path, "resnet50_coco_best_v2.1.0.h5")
    if not os.path.exists(model_path):
        print('Model not found exiting ...')
        exit(0)
    from imageai.Detection import ObjectDetection
    detector = ObjectDetection()
    detector.setModelTypeAsRetinaNet()
    detector.setModelPath(model_path)
    detector.loadModel()
    start(conn)
    t1_stop = perf_counter()
    print("Time elapsed {} seconds".format(t1_stop - t1_start))
