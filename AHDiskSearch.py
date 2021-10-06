import datetime
import multiprocessing
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox, filedialog

from tkdocviewer import DocViewer
from ttkbootstrap import Style

from AHFTSearch import FullTextSearch

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist.AHDiskIndexer import start as ah_disk_indexer
from dist.AHFullTextIndexer import start as ah_full_text_indexer
from dist.AHObjectDetector import start as ah_image_recognition
from dist.audio_to_text import start as audio_to_text
from dist.shared import LOGGER, create_connection, get_sub_string, DATE_TIME_FORMAT, BASE_DIR


class App(tk.Tk, FullTextSearch):
    list_box_cols = ('Filename', 'Size', 'Created', 'Modified')
    indexers = (ah_disk_indexer, ah_full_text_indexer, ah_image_recognition, audio_to_text)
    indexer_process: multiprocessing.Process = None

    def __init__(self):
        super(App, self).__init__()
        self.conn = create_connection()
        self.config_file = os.path.join(BASE_DIR, 'dist', 'ahsearch.config')
        self.title('Full Disk Search')
        self.geometry('1065x555+30+30')
        self.iconbitmap(os.path.join(BASE_DIR, 'dist', 'ahsearch.ico'))
        style = Style(theme="cosmo")
        style.configure("TProgressbar", thickness=5)
        # style.configure("Treeview", borderwidth=0)
        self.style = style.master
        self.resizable(0, 0)
        self.query_var = tk.StringVar()
        self.dock_viewer = None
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
        self.home_page()

    def start_progress(self):
        self.progress_frame.tkraise()
        self.pb.start(5)

    def stop_progress(self):
        self.empty_frame.tkraise()
        self.pb.stop()

    def start_indexing(self):
        self.stop_indexing()
        self.start_progress()
        indexer_index = self.indexer_type.get() - 1
        indexer = self.indexers[indexer_index]
        self.indexer_process = multiprocessing.Process(target=indexer)
        self.indexer_process.start()
        self.monitor()

    def stop_indexing(self):
        if self.indexer_process and self.indexer_process.is_alive():
            self.indexer_process.terminate()

    def monitor(self):
        """ Monitor the download thread """
        if self.indexer_process.is_alive():
            self.after(100, lambda: self.monitor())
        else:
            self.stop_progress()

    def read_config(self, widget):
        file = open(self.config_file, "r")
        for line in file.readlines():
            line = line.strip("\n")
            widget.insert("end", line)
        file.close()

    def save_config(self, widget):
        self.start_progress()
        file = open(self.config_file, "w")
        for i in range(widget.size()):
            file.write(widget.get(i))
            file.write("\n")
        file.close()
        self.stop_progress()

    def remove_item(self, widget):
        for i in widget.curselection():
            widget.delete(i)

    def file_preview(self, widget=None):
        cur_item = widget.focus()
        file = widget.item(cur_item)['values'][0]
        self.dock_viewer.display_file(file)

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
            for index, row in enumerate(files):
                filename, size, creation, modification = row
                utc_create = datetime.datetime.fromtimestamp(creation).strftime(DATE_TIME_FORMAT)
                utc_mod = datetime.datetime.fromtimestamp(modification).strftime(DATE_TIME_FORMAT)
                widget.insert("", "end", values=(filename, int(size), utc_create, utc_mod))
        except AssertionError as error:
            self.message(error.args[0], "Error")
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
        answer = filedialog.askdirectory(parent=self, initialdir=os.getcwd(), title="Please select a folder:")
        folder_list.insert("end", answer)

    def destroy_active_frames(self):
        if self.active_frames:
            for frame in self.active_frames: frame.destroy()

    def config_page(self):
        self.destroy_active_frames()
        self.indexer_type = tk.IntVar()
        file_frame = ttk.Frame(self)
        file_frame.columnconfigure(0, weight=1)
        file_frame.columnconfigure(1, weight=15)
        file_frame.columnconfigure(2, weight=1)
        label = ttk.Label(file_frame, text='Folder: ')
        label.grid(column=0, row=0, sticky=tk.W)
        file_entry = ttk.Entry(file_frame, textvariable=self.query_var, width=131)
        file_entry.focus()
        file_entry.grid(column=1, row=0, sticky=tk.EW)
        search_button = ttk.Button(file_frame, text='Select')
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
        self.indexer_type.set(1)
        filename_indexer = ttk.Radiobutton(radio_frame, text='File Indexer', variable=self.indexer_type, value=1)
        filename_indexer.grid(column=1, **grid_params)
        fulltext_indexer = ttk.Radiobutton(radio_frame, text='Full Text', variable=self.indexer_type, value=2)
        fulltext_indexer.grid(column=2, **grid_params)
        image_objects_indexer = ttk.Radiobutton(radio_frame, text='Image Recognition', variable=self.indexer_type,
                                                value=3)
        image_objects_indexer.grid(column=3, **grid_params)
        audio_search_indexer = ttk.Radiobutton(radio_frame, text='Audio To Text', variable=self.indexer_type, value=4)
        audio_search_indexer.grid(column=4, **grid_params)
        radio_frame.grid(column=0, row=1, sticky=tk.EW, padx=10, ipady=5)

        list_frame = ttk.Frame(self)
        list_frame.columnconfigure(0, weight=17)
        list_box = tk.Listbox(list_frame, width=68, height=23)
        list_box.grid(row=0, column=0, sticky=tk.NSEW)
        search_button.config(command=lambda widget=list_box: self.folder_select(folder_list=widget))
        search_button.grid(column=2, row=0, sticky=tk.E)

        list_frame.grid(column=0, row=3, sticky=tk.NSEW, padx=10, pady=(0, 10))

        action_frame = ttk.Frame(self)
        action_frame.columnconfigure(0, weight=13)
        action_frame.columnconfigure(1, weight=1)
        action_frame.columnconfigure(2, weight=1)
        action_frame.columnconfigure(3, weight=1)
        action_frame.columnconfigure(4, weight=1)
        grid_params = dict(row=0, sticky=tk.E)
        delete_button = ttk.Button(action_frame, text='Delete', width=15)
        delete_button.config(command=lambda _widget=list_box: self.remove_item(widget=_widget))
        delete_button.grid(column=1, **grid_params)
        save_button = ttk.Button(action_frame, text='Save', width=15)
        save_button.config(command=lambda _widget=list_box: self.save_config(widget=_widget))
        save_button.grid(column=2, **grid_params)
        indexer_button = ttk.Button(action_frame, text='Start Indexing', width=15)
        indexer_button.config(command=self.start_indexing)
        indexer_button.grid(column=3, **grid_params)
        stop_indexer_button = ttk.Button(action_frame, text='Stop Indexing')
        stop_indexer_button.config(command=self.stop_indexing)
        stop_indexer_button.grid(column=4, **grid_params)
        action_frame.grid(column=0, row=4, sticky=tk.NSEW, padx=10, pady=(0, 10), ipady=5)

        self.read_config(list_box)
        self.active_frames = (file_frame, radio_frame, list_frame, action_frame)

    def home_page(self):
        self.destroy_active_frames()
        self.search_type = tk.IntVar()
        query_frame = ttk.Frame(self)
        query_frame.columnconfigure(0, weight=1)
        query_frame.columnconfigure(1, weight=15)
        query_frame.columnconfigure(2, weight=1)
        label = ttk.Label(query_frame, text='Search: ')
        label.grid(column=0, row=0, sticky=tk.W)
        self.query_var.set('')
        query_entry = ttk.Entry(query_frame, textvariable=self.query_var, width=130)
        query_entry.focus()
        query_entry.grid(column=1, row=0, sticky=tk.EW)
        query_frame.grid(column=0, row=0, sticky=tk.NSEW, padx=10, pady=(10, 10))

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
        preview_list_frame.columnconfigure(0, weight=7)
        # preview_list_frame.columnconfigure(1, weight=1)
        preview_list_frame.columnconfigure(2, weight=4)
        self.dock_viewer = DocViewer(preview_list_frame, width=100)
        self.dock_viewer.grid(row=0, column=2, sticky=tk.NSEW)
        params = dict(columns=self.list_box_cols, show='headings', height=20)
        list_box = ttk.Treeview(preview_list_frame, **params)
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

        list_box.column('Filename', width=350)
        list_box.column('Size', width=90)
        list_box.column('Created', width=115)
        list_box.column('Modified', width=115)
        list_box.bind("<<TreeviewSelect>>", lambda event, widget=list_box: self.file_preview(widget=widget))
        list_box.grid(row=0, column=0, sticky=tk.EW)

        search_button = ttk.Button(query_frame, text='Search')
        search_button.config(command=lambda widget=list_box: self.fill_treeview(widget=widget))
        search_button.grid(column=2, row=0, sticky=tk.E)

        preview_list_frame.grid(column=0, row=4, sticky=tk.NSEW, padx=10, pady=(0, 10))
        list_box.bind("<Double-1>", lambda event, _event='file', widget=list_box: self.open_target(_event, widget))
        self.bind('<Return>', lambda event, widget=list_box: self.fill_treeview(widget=widget))
        self.active_frames = (query_frame, radio_frame, preview_list_frame)


if __name__ == '__main__':
    app = App()
    app.mainloop()
