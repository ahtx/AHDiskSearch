import sys
import os
from sqlite3 import Error
from time import perf_counter

import pandas as pd
from imageai.Detection import ObjectDetection

from dist.shared import create_connection, BASE_DIR


def create_table(conn):
    query = "CREATE TABLE image_objects (filename TEXT PRIMARY KEY, objects TEXT, probabilities TEXT);"
    try:
        conn.cursor().execute(query)
    except Error as e:
        print(f"Warning: {e}")


def entry_exists(conn, v1):
    sql = "SELECT filename FROM image_objects WHERE filename = ?"
    cur = conn.cursor().execute(sql, (v1,))
    rows = cur.fetchall()
    if len(rows) == 0:
        return False
    else:
        return True


def insert_entry(conn, v1, v2, v3):
    sql = "INSERT INTO image_objects(filename,objects,probabilities) VALUES(?,?,?)"
    cur = conn.cursor()
    cur.execute(sql, (v1, v2, v3))
    conn.commit()


def start(conn):
    query = "SELECT filename FROM files WHERE filename LIKE '%.jpg' "
    try:
        df = pd.read_sql_query(query, conn)
        for index, row in enumerate(df.values):
            filename = row[0]
            print(f"{index + 1} Processing {filename}")
            if not entry_exists(conn, filename):
                try:
                    xyz, detections = detector.detectObjectsFromImage(input_image=filename, output_type="array")
                    objects = []
                    probabilities = []
                    for eachObject in detections:
                        objects.append(eachObject["name"])
                        probabilities.append(eachObject["percentage_probability"])
                    insert_entry(conn, filename, str(objects), str(probabilities))
                except:
                    print(f"Exception occurred with {filename}")
            else:
                print(f"{filename} has already been catalogued")
    except:
        print("SQL Error")


if __name__ == '__main__':
    conn = create_connection()
    try:
        assert conn, 'Database connection error'
        create_table(conn)
        model_file = os.path.join(BASE_DIR, 'dist', 'resnet50_coco_best_v2.1.0.h5')
        assert os.path.exists(model_file), 'resnet50_coco_best_v2.1.0.h5 is required'
    except Exception as error:
        print("Error: ", str(error))
        sys.exit()
    print("Starting object recognition process...")
    t1_start = perf_counter()
    detector = ObjectDetection()
    detector.setModelTypeAsRetinaNet()
    detector.setModelPath(model_file)
    detector.loadModel()
    t1_stop = perf_counter()
    print("Time elapsed {} seconds".format(t1_stop - t1_start))
