import itertools
import logging
import os
import pickle
import sys
from collections import defaultdict
from time import perf_counter
import win32api
import win32event
import winerror
from TextSpitter import TextSpitter

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist.shared import create_connection, BASE_DIR, LOGGER_TIME_FORMAT, Stats

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
    logging.info("AHFullTextIndexer is already running")
    sys.exit(0)


def dump_pickle(data):
    pickle_file = os.path.join(BASE_DIR, 'dist', 'fulltext.idx.pkl')
    with open(pickle_file, "wb") as tf:
        pickle.dump(data, tf)


def get_pickled_files():
    pickle_file = os.path.join(BASE_DIR, 'dist', 'fulltext.idx.pkl')
    if not os.path.exists(pickle_file):
        return []
    with open(pickle_file, 'rb') as p_file:
        result_set = pickle.load(p_file).values()
        files = list(map(lambda x: x.keys(), result_set))
        files = set(itertools.chain(*files))
    return files


def update_big_idx(filename, full_text, big_idx):
    full_text = full_text.lower()
    for word in set(full_text.split(" ")):
        if not word: continue
        word = word.strip(".,;:\"'!@#$%^&*()-+=<>?,./[]|")
        word = word.replace('\n', '')
        stats = os.stat(filename)
        stats = Stats(*[full_text.count(word.lower()), stats.st_size, stats.st_mtime])
        big_idx[word][filename] = stats
    return big_idx


def start():
    exclude = get_pickled_files()
    query = "SELECT filename FROM files WHERE (filename LIKE '%.txt' OR filename LIKE '%.docx' "
    query += "OR filename LIKE '%.pdf%') AND filename NOT IN ({})".format(','.join('?' * len(exclude)))
    big_idx = defaultdict(dict)
    try:
        conn = create_connection()
        assert conn, "Index database connection failure"
        filenames = set(itertools.chain.from_iterable(conn.cursor().execute(query, list(exclude)).fetchall()))
        total = len(filenames)
        for index, filename in enumerate(filenames):
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
