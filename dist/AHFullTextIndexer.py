import itertools
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
from dist.shared import create_connection, DIST_DIR, LOGGER, Stats, read_path_config, kb_to_mbs, remove_entry


def dump_pickle(data, pickle_file):
    with open(pickle_file, "+wb") as tf:
        pickle.dump(data, tf)


def get_existing_or_default(pickle_file):
    if not os.path.exists(pickle_file):
        return defaultdict(dict)
    with open(pickle_file, 'rb') as p_file:
        result_set = pickle.load(p_file)
    return result_set


def get_pickled_files(pickle_file):
    if not os.path.exists(pickle_file):
        return []
    with open(pickle_file, 'rb') as p_file:
        result_set = pickle.load(p_file).values()
        files = list(map(lambda x: x.keys(), result_set))
        files = set(itertools.chain(*files))
    return files


def update_big_idx(filename, full_text, big_idx):
    words = set(full_text.lower().split())
    for word in words:
        if not word: continue
        word = word.strip(".,;:\"'!@#$%^&*()-+=<>?,./[]|")
        word = word.replace('\n', '').replace('(', '').replace(')', '')
        word.lower()
        stats = os.stat(filename)
        stats = Stats(*[full_text.count(word), stats.st_size, stats.st_mtime])
        big_idx[word][filename] = stats
    return big_idx


def start():
    LOGGER.warning("Starting full text indexing process...")
    pickle_file = os.path.join(DIST_DIR, 'fulltext.idx.pkl')
    t1_start = perf_counter()
    exclude = get_pickled_files(pickle_file)
    cond = "(filename LIKE '%.txt' OR filename LIKE '%.docx' OR filename LIKE '%.pdf%')"
    query = f"SELECT filename FROM files WHERE  {cond}"
    query += " AND filename NOT IN ({})".format(','.join('?' * len(exclude)))
    big_idx = get_existing_or_default(pickle_file)
    try:
        conn = create_connection()
        assert conn, "Index database connection failure"
        filenames = set(itertools.chain.from_iterable(conn.cursor().execute(query, list(exclude)).fetchall()))
        total = len(filenames)
        for index, filename in enumerate(filenames):
            if not os.path.exists(filename):
                remove_entry(filename)
                continue
            file_stats = os.stat(filename)
            file_size = kb_to_mbs(file_stats.st_size)
            LOGGER.warning(f"Indexing [{file_size}] {filename}: {index + 1} out of {total}")
            if file_size > float(read_path_config().get('file_size', 5)): continue
            extension = filename.split('.')[-1]
            if os.path.isfile(filename) and extension in ("txt", "pdf", "docx"):
                try:
                    full_text = TextSpitter(filename=filename)
                    full_text = full_text.decode('utf-8') if isinstance(full_text, bytes) else full_text
                except Exception as err:
                    raise err
                    continue
                big_idx = update_big_idx(filename, full_text, big_idx)
        dump_pickle(big_idx, pickle_file)
    except Exception as err:
        LOGGER.error(err)
    t2_stop = perf_counter()
    LOGGER.warning("Time elapsed {} seconds".format(t2_stop - t1_start))


if __name__ == '__main__':
    # Disallowing Multiple Instance
    mutex = win32event.CreateMutex(None, 1, 'mutex_AHFullTextIndexer')
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        mutex = None
        LOGGER.warning("AHFullTextIndexer is already running")
        sys.exit(0)
    start()
