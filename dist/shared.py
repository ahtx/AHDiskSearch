import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def create_connection():
    try:
        db_file = os.path.join(BASE_DIR, 'dist', 'filesystem.db')
        print(db_file)
        return sqlite3.connect(db_file)
    except Exception as e:
        print(e)
