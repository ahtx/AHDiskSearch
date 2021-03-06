import os
import sys
from pathlib import Path

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileMovedEvent

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist.shared import create_connection, LOGGER, read_path_config


def is_in_watch_list(target: str):
    in_watch_list = False
    for path in read_path_config().get('included', []):
        if target.lower().startswith(path.strip()):
            in_watch_list = True
            break
    return in_watch_list


def entry_exists(conn, table, filename):
    try:
        sql = f"SELECT filename FROM {table} WHERE filename = ?"
        row = conn.cursor().execute(sql, (filename,)).fetchone()
        return True if row else False
    except Exception as error:
        LOGGER.warning(error)
        return False


def insert_values(conn, filename: str):
    try:
        file_stats = os.stat(filename)
        values = (filename, file_stats.st_size, file_stats.st_ctime, file_stats.st_mtime)
        query = "INSERT INTO files(filename,size,creation,modification) VALUES(?,?,?,?) "
        conn.cursor().execute(query, values)
        conn.commit()
        LOGGER.warning(f"Saved {filename}")
    except Exception as error:
        LOGGER.error(error)


def update_modified(conn, filename):
    file_stats = os.stat(filename)
    try:
        query = "UPDATE files SET size = ?, modification = ? WHERE filename = ? "
        conn.cursor().execute(query, (file_stats.st_size, file_stats.st_mtime, filename))
        conn.commit()
        LOGGER.warning(f"UPDATED {filename}")
    except Exception as error:
        LOGGER.warning(error)


def update_filenames(conn, existing, new):
    for table in ('files', 'image_objects', 'voices'):
        exists = entry_exists(conn, table, existing)
        if exists:
            try:
                query = f"UPDATE {table} SET filename = ? WHERE filename = ? "
                conn.cursor().execute(query, (new, existing))
                conn.commit()
                LOGGER.warning(f"Updated {existing} To {new}")
            except Exception as error:
                LOGGER.warning(error)
        else:
            insert_values(conn, new)


def get_windows_path(file_path):
    return str(Path(file_path).absolute())


def delete_file(conn, filename):
    for table in ('files', 'image_objects', 'voices'):
        try:
            query = f"DELETE FROM {table} WHERE filename = ?;"
            conn.cursor().execute(query, (filename,))
            conn.commit()
            LOGGER.warning(f"DELETED {filename}")
        except Exception as error:
            LOGGER.error(error)


class EventHandler(FileSystemEventHandler):

    def on_deleted(self, event):
        conn = create_connection()
        delete_file(conn, get_windows_path(event.src_path))
        conn.close()

    def on_modified(self, event: FileModifiedEvent):
        conn = create_connection()
        update_modified(conn, get_windows_path(event.src_path))
        conn.close()

    def on_moved(self, event: FileMovedEvent):
        src = get_windows_path(event.src_path)
        dest = get_windows_path(event.dest_path)
        if not event.is_directory:
            conn = create_connection()
            update_filenames(conn, src, dest)
            conn.close()

    def on_created(self, event):
        conn = create_connection()
        insert_values(conn, get_windows_path(event.src_path))
        conn.close()


def start():
    observer = Observer()
    event_handler = EventHandler()
    for path in read_path_config().get('included', []):
        path = str(Path(path.strip()).absolute())
        observer.schedule(event_handler, path, recursive=True)
    observer.start()
    observer.join()


if __name__ == '__main__':
    start()
