import os
import pickle

from dist.shared import BASE_DIR


class FullTextSearch:
    def __init__(self):
        pass

    def run_query(self, query):
        query = query.lower()
        pickle_file = os.path.join(BASE_DIR, 'dist', 'fulltext.idx.pkl')
        with open(pickle_file, 'rb') as handle:
            b = pickle.load(handle)
            words = query.split(" ")
            word_list = list(map(lambda x: b[x].keys(), words))
            for word in word_list:
                result = set(word_list[0]).intersection(set(word))
        return result
