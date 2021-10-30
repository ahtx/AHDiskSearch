import os
import pickle
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist.shared import DIST_DIR


class FullTextSearch:
    def __init__(self):
        pass

    def run_query(self, query):
        query = query.lower()
        pickle_file = os.path.join(DIST_DIR, 'fulltext.idx.pkl')
        files = list()
        with open(pickle_file, 'rb') as p_file:
            result_set = pickle.load(p_file)
            for word in query.split():
                result = result_set[word.lower().strip()]
                files = list(set(files).intersection(set(result))) if files else result
        return files
