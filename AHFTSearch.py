import pickle
from sys import argv
import sys

class FullTextSearch:
    def __init__(self):
        pass

    def run_query(self,query):
        s = list()
        query = query.lower()
        #print(query)
        with open('fulltext.idx.pkl', 'rb') as handle:
            b = pickle.load(handle)
            words = query.split(" ")
            wl = list()

            for w in words:
                wl.append(b[w].keys())

            #print(wl)

            s = wl[0]
            for l in wl:
                s = set.intersection(set(s),set(l))

        return(s)


