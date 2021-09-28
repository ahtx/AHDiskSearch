import logging
import os
import pickle
import sys
from collections import defaultdict
from time import perf_counter
import pandas as pd
import win32api
import win32event
import winerror
from TextSpitter import TextSpitter

from dist.shared import create_connection, BASE_DIR, LOGGER_TIME_FORMAT

log_file = os.path.join(BASE_DIR, 'dist', 'full_text_indexer.log')
logging.basicConfig(
    filename=log_file,
    filemode='w',
    format='%(asctime)s-%(levelname)s - %(message)s',
    datefmt=LOGGER_TIME_FORMAT
)

# Disallowing Multiple Instance
mutex = win32event.CreateMutex(None, 1, 'mutex_AHFullTextIndexer')
if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    mutex = None
    logging.info("AHFullTextIndexer already running")
    sys.exit(0)


def dump_pickle(data):
    pickle_file = os.path.join(BASE_DIR, 'dist', 'fulltext.idx.pkl')
    with open(pickle_file, "wb") as tf:
        pickle.dump(data, tf)


def update_big_idx(filename, full_text, big_idx):
    full_text = full_text.lower()
    for word in set(full_text.split(" ")):
        if not word: continue
        word = word.strip(".,;:\"'!@#$%^&*()-+=<>?,./[]|")
        big_idx[word][filename] = full_text.count(word)
    return big_idx


def start():
    query = "SELECT filename FROM files WHERE filename LIKE '%.txt' OR filename LIKE '%.docx' "
    query += "OR filename LIKE '%.pdf%'"
    big_idx = defaultdict(dict)
    try:
        conn = create_connection()
        assert conn, "DB connection failure"
        df = pd.read_sql_query(query, conn)
        total = df.count().filename
        for index, row in enumerate(df.values):
            filename = row[0]
            extension = filename.split('.')[-1]
            if os.path.isfile(filename) and extension in ("txt", "pdf", "docx"):
                logging.info(f"Indexing {index + 1} out of {total} {filename}")
                try:
                    full_text = TextSpitter(filename)
                except Exception as error:
                    logging.error(error)
                    continue
                big_idx = update_big_idx(filename, full_text, big_idx)
        dump_pickle(big_idx)
    except Exception as error:
        logging.error(error)


if __name__ == '__main__':
    logging.info("Starting full text indexing process...")
    t1_start = perf_counter()
    start()
    t1_stop = perf_counter()
    logging.info("Time elapsed {} seconds".format(t1_stop - t1_start))
