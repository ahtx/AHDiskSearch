import itertools
import sys
import os
from sqlite3 import IntegrityError
from time import perf_counter

import win32api
import win32event
import winerror

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist.shared import create_connection, DIST_DIR, LOGGER, remove_entry


def entry_exists(conn, v1):
    sql = "SELECT filename FROM image_objects WHERE filename = ?"
    row = conn.cursor().execute(sql, (v1,)).fetchone()
    return True if row else False


def insert_entry(conn, v1, v2, v3):
    sql = "INSERT INTO image_objects(filename,objects,probabilities) VALUES(?,?,?)"
    cur = conn.cursor()
    cur.execute(sql, (v1, v2, v3))
    conn.commit()


def start():
    conn = create_connection()
    try:
        assert conn, 'Database connection error'
        model_file = os.path.join(DIST_DIR, 'resnet50_coco_best_v2.1.0.h5')
        assert os.path.exists(model_file), 'resnet50_coco_best_v2.1.0.h5 is required'
    except Exception as err:
        LOGGER.error(err)
        sys.exit()
    LOGGER.warning("Starting object recognition process...")
    t1_start = perf_counter()
    from imageai.Detection import ObjectDetection
    detector = ObjectDetection()
    detector.setModelTypeAsRetinaNet()
    detector.setModelPath(model_file)
    detector.loadModel()
    query = "SELECT filename FROM files WHERE filename LIKE '%.jpg' "
    try:
        results = list(itertools.chain.from_iterable(conn.cursor().execute(query).fetchall()))
        total = len(results)
        for index, filename in enumerate(results):
            if not os.path.exists(filename):
                remove_entry(filename)
            LOGGER.warning(f"Processing {filename}:  {index + 1} out of {total}")
            if entry_exists(conn, filename):
                continue
            try:
                xyz, detections = detector.detectObjectsFromImage(input_image=filename, output_type="array")
                objects = []
                probabilities = []
                for eachObject in detections:
                    objects.append(eachObject["name"])
                    probabilities.append(eachObject["percentage_probability"])
                insert_entry(conn, filename, str(objects), str(probabilities))
            except IntegrityError as err:
                LOGGER.warning(err)
            except Exception as err:
                LOGGER.error(err)
    except Exception as err:
        LOGGER.error(err)
    t2_stop = perf_counter()
    LOGGER.info("Time elapsed {} seconds".format(t2_stop - t1_start))


if __name__ == '__main__':
    # Disallowing Multiple Instance
    mutex = win32event.CreateMutex(None, 1, 'mutex_AHObjectDetector')
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        mutex = None
        LOGGER.warning("AHObjectDetector is already running")
        sys.exit(0)
    start()
