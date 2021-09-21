import pickle
from sys import argv
import sys


class FullTextSearch:
    def __init__(self):
        pass

    def run_query(self, query):
        query = query.lower()
        with open('fulltext.idx.pkl', 'rb') as handle:
            b = pickle.load(handle)
            words = query.split(" ")
            wl = list(map(lambda x: b[x].keys(), words))
            for l in wl:
                s = set(wl[0]).intersection(set(l))
        return s
