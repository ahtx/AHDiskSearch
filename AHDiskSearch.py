import datetime
import functools
import json
import multiprocessing
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

import keyboard
import win32api
import win32event
import winerror
from TextSpitter import TextSpitter
from tkdocviewer import DocViewer
from ttkbootstrap import Style

from AHFTSearch import FullTextSearch

# sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist import AHDiskIndexer, audio_to_text, AHFullTextIndexer, AHObjectDetector
from dist.shared import LOGGER, create_connection, get_sub_string, DATE_TIME_FORMAT, BASE_DIR


class ProcessAsync(multiprocessing.Process):
    def __init__(self, target):
        super(ProcessAsync, self).__init__()
        self.target = target

    def run(self) -> None:
        self.target()


class App(tk.Tk, FullTextSearch):
    hotkey = "ctrl+shift+f"
    list_box_cols = ('Filename', 'Size', 'Created', 'Modified')
    indexers = (AHDiskIndexer.start, AHFullTextIndexer.start, AHObjectDetector.start, audio_to_text.start)
    indexer_process: ProcessAsync

    def __init__(self):
        keyboard.add_hotkey(self.hotkey, self.find_window_movetop, args=())
        super(App, self).__init__()
        self.conn = create_connection()
        self.config_file = os.path.join(BASE_DIR, 'dist', 'ahsearch.config')
        self.title('Full Disk Search')
        self.geometry('1065x555+30+30')
        self.iconbitmap(os.path.join(BASE_DIR, 'dist', 'ahsearch.ico'))
        style = Style(theme="cosmo")
        style.configure('TEntry', font=('Helvetica', 12))
        style.configure("TProgressbar", thickness=5)
        self.style = style.master
        highlight_color = '#96a89b'
        style.map('TButton', bordercolor=[('focus !disabled', highlight_color)])
        style.map('TEntry', bordercolor=[('focus !disabled', highlight_color)])
        style.map('TRadiobutton', foreground=[('focus', highlight_color)])
        style.map('Treeview', bordercolor=[('focus', highlight_color)])
        self.resizable(0, 0)
        self.query_var = tk.StringVar()
        self.dock_viewer: DocViewer
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        menubar.add_command(label='Home', command=self.home_page)
        menubar.add_command(label='Indexer Config', command=self.config_page)
        # Progress frame
        self.progress_frame = ttk.Frame(self)

        # configrue the grid to place the progress bar is at the center
        self.progress_frame.columnconfigure(0, weight=1)
        self.progress_frame.rowconfigure(0, weight=1)

        # progressbar
        self.pb = ttk.Progressbar(self.progress_frame, orient=tk.HORIZONTAL, mode='indeterminate')
        self.pb.grid(row=0, column=0, sticky=tk.EW)

        # place the progress frame
        self.progress_frame.grid(row=2, column=0, sticky=tk.NSEW, padx=10, pady=(0, 2))

        self.empty_frame = tk.Frame(self, bg='#007bff')
        self.empty_frame.columnconfigure(0, weight=1)
        self.empty_frame.grid(row=2, column=0, sticky=tk.NSEW, padx=10, pady=(0, 2))
        self.active_frames = None
        self.show_preview = True
        self.indexer_type = tk.IntVar()
        self.indexer_type.set(1)
        self.home_page()

    def find_window_movetop(self):
        self.wm_deiconify()


    def start_progress(self):
        self.progress_frame.tkraise()
        self.pb.start(5)

    def stop_progress(self):
        self.empty_frame.tkraise()
        self.pb.stop()

    def start_indexing(self, current_indexer=0):
        indexer_index = self.indexer_type.get() - 1
        if self.indexer_type.get() < 5:
            self.stop_indexing()
            current_indexer = indexer_index
        self.start_progress()
        indexer = self.indexers[current_indexer]
        self.indexer_process = ProcessAsync(target=indexer)
        self.indexer_process.start()
        self.monitor(current_indexer)

    def stop_indexing(self):
        if hasattr(self, 'indexer_process') and self.indexer_process and self.indexer_process.is_alive():
            self.indexer_process.terminate()
        self.stop_progress()

    def monitor(self, current_indexer=0):
        """ Monitor the download thread """
        if self.indexer_process.is_alive():
            self.after(100, lambda: self.monitor(current_indexer))
        elif self.indexer_type.get() == 5:
            self.stop_progress()
            current_indexer += 1
            if current_indexer < 4:
                self.start_indexing(current_indexer)
        else:
            self.stop_progress()

    def write_widget(self, widget, data):
        for line in data:
            line = line.strip("\n")
            widget.insert("end", line)

    def read_data(self):
        with open(self.config_file) as open_file:
            try:
                data = json.load(open_file)
            except json.decoder.JSONDecodeError:
                data = {}
        return data

    def write_config(self, data):
        with open(self.config_file, 'w') as out_file:
            out_file.write(data)

    def read_config(self, included, excluded):
        data = self.read_data()
        self.write_widget(included, data.get('included', []))
        self.write_widget(excluded, data.get('excluded', []))

    def save_config(self, included, excluded):
        self.start_progress()
        included_items = list(included.get(i) for i in range(included.size()))
        excluded_items = list(excluded.get(i) for i in range(excluded.size()))
        data = json.dumps(dict(included=included_items, excluded=excluded_items), indent=4)
        self.write_config(data)
        self.stop_progress()

    def remove_and_get(self, i, widget):
        item = widget.get(i)
        widget.delete(i)
        return item

    def remove_item(self, included, excluded):
        included_removed = set(map(functools.partial(self.remove_and_get, widget=included), included.curselection()))
        excluded_removed = set(map(functools.partial(self.remove_and_get, widget=excluded), excluded.curselection()))
        data = self.read_data()
        included_items = list(set(set(data.get('included', [])) - included_removed))
        excluded_items = list(set(set(data.get('excluded', [])) - excluded_removed))
        data = json.dumps(dict(included=included_items, excluded=excluded_items), indent=4)
        self.write_config(data)

    def file_preview(self, widget=None):
        cur_item = widget.focus()
        file = widget.item(cur_item)['values'][0]
        base, ext = map(str.lower, os.path.splitext(file))
        if ext in ('.pdf', '.docx',):
            self.dock_viewer.display_text(TextSpitter(file)[0:500] + '...')
        elif self.dock_viewer.can_display(file):
            self.dock_viewer.display_file(file, pages=1)
        else:
            file_stats = os.stat(file)
            message = f"File: {file}\n"
            message += "##############################\n"
            message += f"Size: {file_stats.st_size}\n"
            message += f"Creation: {self.epoch_to_date(file_stats.st_ctime)}\n"
            message += f"Modification: {self.epoch_to_date(file_stats.st_mtime)}"
            self.dock_viewer.display_text(message)

    def show_hide_preview(self, widget=None):
        self.show_preview = False if self.show_preview else True
        if self.show_preview:
            self.dock_viewer.grid(row=0, column=2, sticky=tk.NSEW)
            widget.column('Filename', width=420)
            widget.column('Size', width=90)
            widget.column('Created', width=115)
            widget.column('Modified', width=115)
        else:
            self.dock_viewer.grid_forget()
            widget.column('Filename', width=590)
            widget.column('Size', width=120)
            widget.column('Created', width=160)
            widget.column('Modified', width=160)
        widget.update()

    def epoch_to_date(self, epoch_time):
        return datetime.datetime.fromtimestamp(epoch_time).strftime(DATE_TIME_FORMAT)

    def message(self, message, name="Error"):
        methods = dict(Error=messagebox.showerror, Info=messagebox.showinfo, Warning=messagebox.showwarning)
        methods[name](title=name, message=message)

    def get_query(self, search):
        search_type = self.search_type.get()
        if search_type == 1:
            query = "SELECT * FROM files WHERE "
            query += get_sub_string(search.split(" "), " AND filename LIKE ", "filename LIKE ", True)
        elif search_type == 2:
            text_files = list(self.run_query(search))[:100]
            query = "SELECT * FROM files WHERE "
            query += get_sub_string(text_files, " OR filename = ")
        elif search_type == 3:
            query = "SELECT files.filename, files.size, files.creation, files.modification FROM files "
            query += "INNER JOIN image_objects on files.filename=image_objects.filename "
            query += "WHERE files.filename = image_objects.filename AND "
            arg_1 = " AND image_objects.objects LIKE "
            arg_2 = "image_objects.objects LIKE "
            query += get_sub_string(search.split(" "), arg_1, arg_2, True)
        else:
            query = "SELECT files.filename, files.size, files.creation, files.modification FROM files "
            query += "INNER JOIN voices on files.filename=voices.filename "
            query += "WHERE files.filename = voices.filename AND "
            query += get_sub_string(search.split(" "), " AND voices.words LIKE ", "voices.words LIKE ", True)
        return query

    def fill_treeview(self, widget):
        query = self.query_var.get()
        try:
            assert query, "Please enter a query!"
            query = self.get_query(query)
            widget.delete(*widget.get_children())
            assert not query.lower().endswith('where '), "Data not found!"
            files = self.conn.cursor().execute(query).fetchall()
            assert len(files) > 0, f"'{self.query_var.get()}' related data not found."
            for index, row in enumerate(files):
                filename, size, creation, modification = row
                utc_create = self.epoch_to_date(creation)
                utc_mod = self.epoch_to_date(modification)
                widget.insert("", "end", values=(filename, int(size), utc_create, utc_mod))
        except AssertionError as error:
            self.message(error.args[0], "Info")
        except Exception as err:
            LOGGER.error(err)

    def open_target(self, event='file', widget=None):
        try:
            cur_item = widget.focus()
            cur_text = widget.item(cur_item)['values'][0]
            target = cur_text if event == 'file' else str(Path(cur_text).parent)
            os.startfile(target)
        except Exception as error:
            self.message(message=error.args[0])

    def folder_select(self, folder_list):
        answer = filedialog.askdirectory(parent=self, initialdir=os.environ['HOMEPATH'], title="Please select a folder:")
        folder_list.insert("end", str(Path(answer).absolute()))

    def destroy_active_frames(self):
        if self.active_frames:
            for frame in self.active_frames: frame.destroy()

    def config_page(self):
        self.title('Configure Indexing')
        self.destroy_active_frames()
        file_frame = ttk.Frame(self)
        file_frame.columnconfigure(0, weight=16)
        file_frame.columnconfigure(1, weight=2)
        file_frame.columnconfigure(2, weight=16)
        search_button = ttk.Button(file_frame, text='Select To Include', width=71)
        search_button.grid(column=0, row=0, sticky=tk.W, padx=(0, 5))
        exclude_button = ttk.Button(file_frame, text="Select To Exclude", width=71, style='secondary.TButton')
        exclude_button.grid(column=2, row=0, sticky=tk.E)
        file_frame.grid(column=0, row=0, sticky=tk.NSEW, padx=10, pady=(10, 10))
        radio_frame = ttk.LabelFrame(self, text='Parameters')
        radio_frame.columnconfigure(0, weight=1)
        radio_frame.columnconfigure(1, weight=1)
        radio_frame.columnconfigure(2, weight=1)
        radio_frame.columnconfigure(3, weight=1)
        radio_frame.columnconfigure(4, weight=1)
        radio_frame.columnconfigure(5, weight=1)
        radio_frame.columnconfigure(6, weight=1)
        grid_params = dict(row=2, sticky=tk.W)
        ttk.Label(radio_frame, text='Select Indexer: ').grid(column=0, **grid_params)
        filename_indexer = ttk.Radiobutton(radio_frame, text='File Indexer', variable=self.indexer_type, value=1)
        filename_indexer.grid(column=1, **grid_params)
        fulltext_indexer = ttk.Radiobutton(radio_frame, text='Full Text', variable=self.indexer_type, value=2)
        fulltext_indexer.grid(column=2, **grid_params)
        image_objects_indexer = ttk.Radiobutton(radio_frame, text='Image Recognition', variable=self.indexer_type,
                                                value=3)
        image_objects_indexer.grid(column=3, **grid_params)
        audio_search_indexer = ttk.Radiobutton(radio_frame, text='Audio To Text', variable=self.indexer_type, value=4)
        audio_search_indexer.grid(column=4, **grid_params)

        all_indexer = ttk.Radiobutton(radio_frame, text='All Indexer', variable=self.indexer_type, value=5)
        all_indexer.grid(column=5, **grid_params)
        radio_frame.grid(column=0, row=1, sticky=tk.EW, padx=10, ipady=5)

        list_frame = ttk.Frame(self)
        list_frame.columnconfigure(0, weight=16)
        list_frame.columnconfigure(1, weight=2)
        list_frame.columnconfigure(2, weight=16)
        ttk.Label(list_frame, text="Included Folders").grid(row=0, column=0, sticky=tk.W)
        list_box = tk.Listbox(list_frame, width=70, height=21, borderwidth=0, selectmode='multiple')
        list_box.grid(row=1, column=0, sticky=tk.EW)
        search_button.config(command=lambda widget=list_box: self.folder_select(folder_list=widget))
        list_frame.grid(column=0, row=3, sticky=tk.NSEW, padx=10, pady=(0, 10))
        ttk.Label(list_frame, text="Excluded Folders").grid(row=0, column=2, sticky=tk.W)
        list_box_excluded = tk.Listbox(list_frame, width=70, height=21, borderwidth=0, selectmode='multiple')
        exclude_button.config(command=lambda widget=list_box_excluded: self.folder_select(folder_list=widget))
        list_box_excluded.grid(row=1, column=2, sticky=tk.EW)

        action_frame = ttk.Frame(self)
        action_frame.columnconfigure(0, weight=13)
        action_frame.columnconfigure(1, weight=1)
        action_frame.columnconfigure(2, weight=1)
        action_frame.columnconfigure(3, weight=1)
        action_frame.columnconfigure(4, weight=1)
        grid_params = dict(row=0, sticky=tk.E)
        delete_button = ttk.Button(action_frame, text='Delete', width=15, style='danger.TButton')
        delete_button.config(
            command=lambda _incl=list_box, _exclu=list_box_excluded: self.remove_item(included=_incl, excluded=_exclu))
        delete_button.grid(column=1, **grid_params)
        save_button = ttk.Button(action_frame, text='Save', width=15)
        save_button.config(
            command=lambda _incl=list_box, _exclu=list_box_excluded: self.save_config(included=_incl, excluded=_exclu))
        save_button.grid(column=2, **grid_params)
        indexer_button = ttk.Button(action_frame, text='Start Indexing', width=15, style='success.TButton')
        indexer_button.config(command=self.start_indexing)
        indexer_button.grid(column=3, **grid_params)
        stop_indexer_button = ttk.Button(action_frame, text='Stop Indexing', style='danger.TButton')
        stop_indexer_button.config(command=self.stop_indexing)
        stop_indexer_button.grid(column=4, **grid_params)
        action_frame.grid(column=0, row=4, sticky=tk.NSEW, padx=10, pady=(0, 10), ipady=5)

        self.read_config(list_box, list_box_excluded)
        self.active_frames = (file_frame, radio_frame, list_frame, action_frame)

    def home_page(self):
        self.title('AH Disk Search')
        self.destroy_active_frames()
        self.search_type = tk.IntVar()
        query_frame = ttk.Frame(self)
        query_frame.columnconfigure(0, weight=1)
        query_frame.columnconfigure(1, weight=17)
        query_frame.columnconfigure(2, weight=1)
        query_frame.columnconfigure(3, weight=2)
        label = ttk.Label(query_frame, text='Search: ')
        label.grid(column=0, row=0, sticky=tk.W)
        self.query_var.set('')
        query_entry = ttk.Entry(query_frame, textvariable=self.query_var, width=114, style='TEntry')
        query_entry.focus()
        query_entry.grid(column=1, row=0, sticky=tk.EW)

        search_button = ttk.Button(query_frame, text='Search')
        search_button.grid(column=2, row=0, sticky=tk.W)

        toggle_preview = ttk.Button(query_frame, text='Toggle Preview', style='warning.TButton')
        toggle_preview.grid(column=3, row=0, sticky=tk.E, padx=2)

        query_frame.grid(column=0, row=0, sticky=tk.EW, padx=10, pady=(10, 10))

        radio_frame = ttk.LabelFrame(self, text='Parameters')
        radio_frame.columnconfigure(0, weight=1)
        radio_frame.columnconfigure(1, weight=1)
        radio_frame.columnconfigure(2, weight=1)
        radio_frame.columnconfigure(3, weight=1)
        radio_frame.columnconfigure(4, weight=1)
        radio_frame.columnconfigure(5, weight=1)
        grid_params = dict(row=2, sticky=tk.W)
        ttk.Label(radio_frame, text='Search type: ').grid(column=0, **grid_params)
        self.search_type.set(1)
        filename = ttk.Radiobutton(radio_frame, text='Filename', variable=self.search_type, value=1)
        filename.grid(column=1, **grid_params)
        fulltext = ttk.Radiobutton(radio_frame, text='Full Text', variable=self.search_type, value=2)
        fulltext.grid(column=2, **grid_params)
        image_objects = ttk.Radiobutton(radio_frame, text='Image Objects', variable=self.search_type, value=3)
        image_objects.grid(column=3, **grid_params)
        audio_search = ttk.Radiobutton(radio_frame, text='Audio Search', variable=self.search_type, value=4)
        audio_search.grid(column=4, **grid_params)
        radio_frame.grid(column=0, row=1, sticky=tk.NSEW, padx=10, ipady=5)

        preview_list_frame = ttk.Frame(self)
        preview_list_frame.columnconfigure(0, weight=200)
        preview_list_frame.columnconfigure(2, weight=4)

        self.dock_viewer = DocViewer(preview_list_frame, width=100, scrollbars='horizontal')
        self.dock_viewer.fit_page(2.9)
        self.dock_viewer.grid(row=0, column=2, sticky=tk.NSEW)

        params = dict(columns=self.list_box_cols, show='headings', height=19)
        list_box = ttk.Treeview(preview_list_frame, **params)
        list_box.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar = ttk.Scrollbar(preview_list_frame, orient="vertical", command=list_box.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        list_box.configure(yscrollcommand=scrollbar.set)

        def treeview_sort_column(col, reverse):
            items = [(list_box.set(k, col), k) for k in list_box.get_children('')]
            items.sort(reverse=reverse)
            for index, (val, k) in enumerate(items):
                list_box.move(k, '', index)
            list_box.heading(col, text=col, command=lambda _col=col: treeview_sort_column(_col, not reverse))

        for col in self.list_box_cols:
            list_box.column(col, minwidth=60, width=100)
            list_box.heading(col, text=col, command=lambda _col=col: treeview_sort_column(_col, False))

        list_box.column('Filename', width=390)
        list_box.column('Size', width=90)
        list_box.column('Created', width=115)
        list_box.column('Modified', width=115)
        list_box.bind("<<TreeviewSelect>>", lambda event, widget=list_box: self.file_preview(widget=widget))
        search_button.config(command=lambda widget=list_box: self.fill_treeview(widget=widget))

        preview_list_frame.grid(column=0, row=4, sticky=tk.NSEW, padx=10, pady=(0, 10))
        list_box.bind("<Double-1>", lambda event, _event='file', widget=list_box: self.open_target(_event, widget))
        self.bind('<Return>', lambda event, widget=list_box: self.fill_treeview(widget=widget))
        toggle_preview.config(command=lambda widget=list_box: self.show_hide_preview(widget=widget))
        self.active_frames = (query_frame, radio_frame, preview_list_frame)


if __name__ == '__main__':
    multiprocessing.freeze_support()
    # Disallowing Multiple Instance
    mutex = win32event.CreateMutex(None, 1, 'mutex_AHDiskSearch')
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        mutex = None
        LOGGER.warning("AHDiskSearch is already running.")
        sys.exit(0)
    app = App()
    app.mainloop()
