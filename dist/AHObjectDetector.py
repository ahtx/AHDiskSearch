import logging
import sys
import os
from time import perf_counter

import pandas as pd
import win32api
import win32event
import winerror
from imageai.Detection import ObjectDetection

from dist.shared import create_connection, BASE_DIR, LOGGER_TIME_FORMAT

log_file = os.path.join(BASE_DIR, 'dist', 'object_indexer.log')
logging.basicConfig(
    filename=log_file,
    filemode='w',
    format='%(asctime)s-%(levelname)s - %(message)s',
    datefmt=LOGGER_TIME_FORMAT
)

# Disallowing Multiple Instance
mutex = win32event.CreateMutex(None, 1, 'mutex_AHObjectDetector')
if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    mutex = None
    logging.info("AHObjectDetector already running")
    sys.exit(0)


def create_table(conn):
    query = "CREATE TABLE image_objects (filename TEXT PRIMARY KEY, objects TEXT, probabilities TEXT);"
    try:
        conn.cursor().execute(query)
    except Exception as error:
        logging.warning(error)


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
            logging.info(f"{index + 1} Processing {filename}")
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
                    logging.warning(f"Exception occurred with {filename}")
            else:
                logging.info(f"{filename} has already been catalogued")
    except Exception as error:
        logging.error(error)


if __name__ == '__main__':
    conn = create_connection()
    try:
        assert conn, 'Database connection error'
        create_table(conn)
        model_file = os.path.join(BASE_DIR, 'dist', 'resnet50_coco_best_v2.1.0.h5')
        assert os.path.exists(model_file), 'resnet50_coco_best_v2.1.0.h5 is required'
    except Exception as error:
        logging.error(error)
        sys.exit()
    logging.info("Starting object recognition process...")
    t1_start = perf_counter()
    detector = ObjectDetection()
    detector.setModelTypeAsRetinaNet()
    detector.setModelPath(model_file)
    detector.loadModel()
    t1_stop = perf_counter()
    logging.info("Time elapsed {} seconds".format(t1_stop - t1_start))
