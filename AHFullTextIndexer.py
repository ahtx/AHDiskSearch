import os
import sqlite3
from time import perf_counter
from sqlite3 import Error
import pandas as pd
import docx
import PyPDF2
from collections import defaultdict
import pickle

db_file = ".\\filesystem.db"

def create_connection(db):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Error as e:
        print(e)
    return conn

def pdf_to_text(filename):
    try:
        pdfFileObject = open(filename, 'rb')
        pdfReader = PyPDF2.PdfFileReader(pdfFileObject)
        doc_text = ""
        for i in range(pdfReader.numPages):
            pageObject = pdfReader.getPage(i)
            doc_text = doc_text + pageObject.extractText()
        pdfFileObject.close()
        return(doc_text)
    except:
        return ""

def docx_to_text(filename):
    try:
        doc = docx.Document(filename)
        fullText = []
        for para in doc.paragraphs:
            fullText.append(para.text)
        return('\n'.join(fullText))
    except:
        return ""

def read_text(filename):
    try:
        file_size = os.path.getsize(filename)
        #print(file_size)
        ret_text = ""
        if(file_size < 5000000):
            f = open(filename,"r")
            all_lines = f.read().splitlines()
            return(" ".join(all_lines))
        else:
            return ""
    except:
        return ""

qu = """SELECT filename FROM files WHERE filename LIKE '%.txt' OR filename LIKE '%.docx' """
# OR filename LIKE '%.docx' or filename LIKE '%.pdf' """

print("Starting full text indexing process...")
t1_start = perf_counter() 

conn = create_connection(db_file)
print(f"{qu}")
try: 
    df = pd.read_sql_query(f"{qu}", conn)
    #print("complete")
except:
    print("SQL Error")

big_idx = defaultdict(dict)


for index, row in df.iterrows():
    filename = row['filename']
    
    filename_only, file_extension = os.path.splitext(filename)
    
    if(file_extension == ".txt"):
        full_text = read_text(filename)
        #print(full_text)
    elif(file_extension == ".pdf"):
        full_text = pdf_to_text(filename)
    elif(file_extension == ".docx"):
        full_text = docx_to_text(filename)
    else:
        continue
    
    full_text = full_text.lower()
    
    print(f"Indexing {filename}")
    for word in set(full_text.split(" ")):
        word = word.strip(".,;:\"'!@#$%^&*()-+=<>?,./[]|")
        big_idx[word][filename] = full_text.count(word)

with open("fulltext.idx.pkl","wb") as tf:
    pickle.dump(big_idx, tf)

t1_stop = perf_counter()
print("Time elapsed {} seconds".format(t1_stop-t1_start))