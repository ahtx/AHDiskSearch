import itertools
import os
import pickle

from dist.shared import BASE_DIR


class FullTextSearch:
    def __init__(self):
        pass

    def run_query(self, query):
        query = query.lower()
        pickle_file = os.path.join(BASE_DIR, 'dist', 'fulltext.idx.pkl')
        with open(pickle_file, 'rb') as p_file:
            result_set = pickle.load(p_file)
            words = query.split(" ")
            files = list(map(lambda x: result_set[x].keys(), words))
            files = set(itertools.chain(*files))
        return files
