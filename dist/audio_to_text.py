import itertools
import os
import sys
from pathlib import Path
from sqlite3 import OperationalError
from time import perf_counter

import moviepy.editor as mp
import win32api
import win32event
import winerror
from pydub import AudioSegment
import speech_recognition as sr
from pydub.silence import split_on_silence

from dist.shared import BASE_DIR, LOGGER, create_connection

# Disallowing Multiple Instance
mutex = win32event.CreateMutex(None, 1, 'mutex_AudioToText')
if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    mutex = None
    LOGGER.warning("AHObjectDetector is already running")
    sys.exit(0)


def create_table(conn):
    query = "CREATE TABLE voices (filename TEXT PRIMARY KEY, words TEXT);"
    try:
        conn.cursor().execute(query)
    except OperationalError as err:
        LOGGER.warning(err)
    except Exception as err:
        LOGGER.error(err)


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


def video_to_audio(filename):
    extension = Path(filename).name.split('.')[-1]
    if extension.lower() not in VIDEO_CODECS:
        return filename
    temp_file = os.path.join(os.environ.get('TEMP'), 'video_audio.wav')
    try:
        clip = mp.VideoFileClip(filename).subclip(0, 20)
        clip.audio.write_audiofile(temp_file)
        return temp_file
    except Exception as error:
        LOGGER.warning(error)
    return temp_file


def get_text(filename):
    # open the file
    try:
        with sr.AudioFile(filename) as source:
            # listen for the data (load audio to memory)
            audio_data = r.record(source)
            # recognize (convert from speech to text)
            text = r.recognize_google(audio_data)
            return text
    except Exception as error:
        LOGGER.warning(error)
        return ""


def get_large_audio_transcription(filename):
    file_size = get_size_mb(filename)
    LOGGER.warning(f"File {filename}: size => {file_size}")
    whole_text = ""
    if file_size < 3:
        whole_text += f"{get_text(filename)} "
    else:
        long_audio = AudioSegment.from_file(filename)
        audio_chunks = split_on_silence(
            long_audio, min_silence_len=500,
            silence_thresh=long_audio.dBFS - 14,
            keep_silence=350
        )

        for audio_chunk in audio_chunks:
            filename = os.path.join(os.getenv('TEMP'), 'chunk.wav')
            audio_chunk.export(filename, format="wav")
            file_size = get_size_mb(filename)
            LOGGER.warning(f"{filename}: SIZE =>> {file_size}")
            if file_size < 3:
                text = get_text(filename)
                whole_text += f" {text}" if whole_text else text
            continue
    return whole_text


def start(conn):
    query = "SELECT filename FROM files WHERE filename "
    query += "LIKE '%.mp3' OR filename LIKE '%.wav%' OR filename LIKE '%.mp4%'"
    try:
        results = list(itertools.chain.from_iterable(conn.cursor().execute(query).fetchall()))
        total = len(results)
        for i, filename in enumerate(results, start=1):
            LOGGER.warning(f"{filename} indexing {i} out of {total}")
            if entry_exists(conn, filename):
                continue
            audio_file = video_to_audio(filename)
            words = get_large_audio_transcription(audio_file).strip()
            LOGGER.warning(f'WORDS: {words}')
            if not words:
                continue
            insert_entry(conn, filename, words.lower())
    except Exception as err:
        LOGGER.error(err)


if __name__ == '__main__':
    FFMPEG = os.path.join(BASE_DIR, 'dist', 'ffmpeg.exe')
    FFPROBE = os.path.join(BASE_DIR, 'dist', 'ffprobe.exe')
    VIDEO_CODECS = ('mp4', )
    AudioSegment.converter = FFMPEG
    AudioSegment.ffprobe = FFPROBE
    recognizer = sr.Recognizer()
    # create a speech recognition object
    r = sr.Recognizer()
    t1_start = perf_counter()
    conn = create_connection()
    create_table(conn)
    start(conn)
    t1_stop = perf_counter()
    LOGGER.info("Time elapsed {} seconds".format(t1_stop - t1_start))
