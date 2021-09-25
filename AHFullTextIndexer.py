import os
import sqlite3
from time import perf_counter
from sqlite3 import Error
import pandas as pd

try:
    import docx
except ModuleNotFoundError as error:
    pass
import PyPDF2
from collections import defaultdict
import pickle


def create_connection():
    try:
        db_file = os.path.join(os.getcwd(), "filesystem.db")
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)


def pdf_to_text(filename):
    try:
        pdf_file_object = open(filename, 'rb')
        pdf_reader = PyPDF2.PdfFileReader(pdf_file_object)
        doc_text = ""
        for i in range(pdf_reader.numPages):
            page_object = pdf_reader.getPage(i)
            doc_text = doc_text + page_object.extractText()
        pdf_file_object.close()
        return doc_text
    except:
        return ""


def docx_to_text(filename):
    try:
        doc = docx.Document(filename)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except ModuleNotFoundError as error:
        pass
    except:
        pass
    return ""


def read_text(filename):
    try:
        file_size = os.path.getsize(filename)
        # print(file_size)
        ret_text = ""
        if file_size < 5000000:
            f = open(filename, "r")
            all_lines = f.read().splitlines()
            return " ".join(all_lines)
        else:
            return ""
    except:
        return ""


def dump_pickle(data):
    with open("fulltext.idx.pkl", "wb") as tf:
        pickle.dump(data, tf)


def update_big_idx(filename, full_text, big_idx):
    full_text = full_text.lower()
    for word in set(full_text.split(" ")):
        word = word.strip(".,;:\"'!@#$%^&*()-+=<>?,./[]|")
        big_idx[word][filename] = full_text.count(word)
    return big_idx


def start():
    qu = "SELECT filename FROM files WHERE filename LIKE '%.txt' OR filename LIKE '%.docx' "
    big_idx = defaultdict(dict)
    try:
        conn = create_connection()
        assert conn, "DB connection failure"
        df = pd.read_sql_query(qu, conn)
        methods = dict(txt=read_text, pdf=pdf_to_text, docx=docx_to_text)
        total = df.count().filename
        for index, row in enumerate(df.values):
            filename = row[0]
            extension = filename.split('.')[-1]
            if os.path.isfile(filename) and extension in ("txt", "pdf", "docx"):
                full_text = methods[extension](filename)
                print(f"Indexing {index + 1} out of {total} {filename}")
                big_idx = update_big_idx(filename, full_text, big_idx)
        dump_pickle(big_idx)
    except Exception as error:
        print("Error =>> ", error.args[0])


if __name__ == '__main__':
    print("Starting full text indexing process...")
    t1_start = perf_counter()
    start()
    t1_stop = perf_counter()
    print("Time elapsed {} seconds".format(t1_stop - t1_start))
