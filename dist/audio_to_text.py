import itertools
import os
import sys
from pathlib import Path
from time import perf_counter

import win32api
import win32event
import winerror
import speech_recognition as sr

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist.shared import DIST_DIR, LOGGER, create_connection, remove_entry


def entry_exists(conn, v1):
    sql = "SELECT filename FROM voices WHERE filename = ?"
    row = conn.cursor().execute(sql, (v1,)).fetchone()
    return True if row else False


def insert_entry(conn, v1, v2):
    sql = "INSERT INTO voices(filename,words) VALUES(?,?)"
    cur = conn.cursor()
    cur.execute(sql, (v1, v2))
    conn.commit()


def get_size_mb(filename):
    return round(os.path.getsize(filename) / (1024 * 1024), 3)


def video_to_audio(filename, codecs):
    extension = Path(filename).name.split('.')[-1]
    if extension.lower() not in codecs:
        return filename
    temp_file = os.path.join(os.environ.get('TEMP'), 'video_audio.wav')
    try:
        ffmpeg = os.path.join(DIST_DIR, 'ffmpeg.exe')
        cmd = f'{ffmpeg} -y -i "{filename}" "{temp_file}" -f wav -hide_banner -loglevel error'
        os.system(cmd)
        return temp_file
    except Exception as error:
        LOGGER.warning(f"Conversion: {error}")
    return temp_file


def get_text(filename, r):
    # open the file
    try:
        with sr.AudioFile(filename) as source:
            # listen for the data (load audio to memory)
            audio_data = r.record(source, duration=30)
            # recognize (convert from speech to text)
            # text = r.recognize_sphinx(audio_data)  # use for offline recognition will require extra dependencies
            text = r.recognize_google(audio_data)
            return text
    except Exception as error:
        LOGGER.warning(f"GET TEXT: {error}")
        return ""


def start():
    LOGGER.warning('Starting audio to text conversion')
    codecs = ('mp4', 'mp3',)
    # create a speech recognition object
    recognizer = sr.Recognizer()
    t1_start = perf_counter()
    conn = create_connection()
    query = "SELECT filename FROM files WHERE filename "
    query += "LIKE '%.mp3' OR filename LIKE '%.wav%' OR filename LIKE '%.mp4%'"
    try:
        results = list(itertools.chain.from_iterable(conn.cursor().execute(query).fetchall()))
        total = len(results)
        for i, filename in enumerate(results, start=1):
            LOGGER.warning(f"{filename} indexing {i} out of {total}")
            try:
                if not os.path.exists(filename):
                    remove_entry(filename)
                    continue
                elif entry_exists(conn, filename):
                    continue
                audio_file = video_to_audio(filename, codecs)
                LOGGER.warning(f'Getting Text: {audio_file}')
                words = get_text(audio_file, recognizer).strip()
                LOGGER.warning(f'WORDS: {words}')
                if not words:
                    continue
                insert_entry(conn, filename, words.lower())
            except Exception as error:
                LOGGER.warning(error)
    except Exception as err:
        LOGGER.error(err)
    t2_stop = perf_counter()
    LOGGER.warning("Time elapsed {} seconds".format(t2_stop - t1_start))


if __name__ == '__main__':
    # Disallowing Multiple Instance
    mutex = win32event.CreateMutex(None, 1, 'mutex_AudioToText')
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        mutex = None
        LOGGER.warning("AudioToText is already running")
        sys.exit(0)
    start()
