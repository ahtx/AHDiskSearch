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

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist import AHDiskIndexer, audio_to_text, AHFullTextIndexer, AHObjectDetector
from dist.shared import LOGGER, create_connection, get_sub_string, DATE_TIME_FORMAT, DIST_DIR, read_path_config, \
    kb_to_mbs, convert_bytes


class ProcessAsync(multiprocessing.Process):
    def __init__(self, target):
        super(ProcessAsync, self).__init__()
        self.target = target

    def run(self) -> None:
        self.target()


class App(tk.Tk, FullTextSearch):
    list_box_cols = ('Filename', 'Module', 'Size', 'Created', 'Modified')
    indexers = (AHDiskIndexer.start, AHFullTextIndexer.start, AHObjectDetector.start, audio_to_text.start)
    indexer_process: ProcessAsync
    query_entry = ""

    def __init__(self):
        super(App, self).__init__()
        self.conn = create_connection()
        self.config_file = os.path.join(DIST_DIR, 'ahsearch.config')
        self.title('Full Disk Search')
        self.geometry('1065x555+30+30')
        self.iconbitmap(os.path.join(DIST_DIR, 'ahsearch.ico'))
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
        menubar.add_command(label='Settings', command=self.settings_page)
        # Progress frame
        self.progress_frame = ttk.Frame(self)

        # configure the grid to place the progress bar is at the center
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
        self.dock_viewer = None
        self.active_frames = None
        self.show_preview = tk.StringVar()
        self.hot_key = tk.StringVar()
        self.search_type = tk.StringVar()
        self.indexer_type = tk.StringVar()
        self.file_size = tk.StringVar()
        data = self.read_data()
        self.hot_key.set(data.get('hot_key', 'ctrl+shift+f'))
        self.show_preview.set(data.get('preview', 'show'))
        keyboard.add_hotkey(self.hot_key.get(), self.find_window_movetop, args=())
        self.file_size.set(data.get('file_size', '5'))
        self.home_page()

    def find_window_movetop(self):
        self.wm_deiconify()
        self.attributes("-topmost", True)
        self.focus_set()
        self.focus_force()
        self.grab_set()
        self.query_entry.focus_set()
        
        # There is a problem here. When window comes to the foreground
        # the query entry field doesn't have focus. So typing won't work
        # until you click on the field first. Need to resolve.
        
        #self.query_entry.focus_force()
        #self.query_entry.grab_set()
        #self.query_entry.grab_set_global()
        
        self.query_entry.focus()
        

    def start_progress(self):
        self.progress_frame.tkraise()
        self.pb.start(5)

    def stop_progress(self):
        self.empty_frame.tkraise()
        self.pb.stop()

    def start_indexing(self, current_indexer=0):
        indexer_value = int(self.indexer_type.get())
        indexer_index = indexer_value - 1
        if indexer_value < 5:
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
        elif int(self.indexer_type.get()) == 5:
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
        try:
            with open(self.config_file) as open_file:
                data = json.load(open_file)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
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
            message += f"Size: {convert_bytes(file_stats.st_size)}\n"
            message += f"Creation: {self.epoch_to_date(file_stats.st_ctime)}\n"
            message += f"Modification: {self.epoch_to_date(file_stats.st_mtime)}"
            self.dock_viewer.display_text(message)

    def show_hide_preview(self, widget=None):
        if self.show_preview.get() == 'show':
            self.dock_viewer.grid(row=0, column=2, sticky=tk.NSEW)
            widget.column('Filename', width=368)
            widget.column('Module', width=50)
            widget.column('Size', width=90)
            widget.column('Created', width=115)
            widget.column('Modified', width=115)
        else:
            self.dock_viewer.grid_forget()
            widget.column('Filename', width=650)
            widget.column('Module', width=50)
            widget.column('Size', width=90)
            widget.column('Created', width=115)
            widget.column('Modified', width=115)
        widget.update()

    def epoch_to_date(self, epoch_time):
        return datetime.datetime.fromtimestamp(epoch_time).strftime(DATE_TIME_FORMAT)

    def message(self, message, name="Error"):
        methods = dict(Error=messagebox.showerror, Info=messagebox.showinfo, Warning=messagebox.showwarning)
        methods[name](title=name, message=message)

    def get_query(self, search):
        search_type = int(self.search_type.get())
        if search_type == 1:
            substr = get_sub_string(search.split(" "), " AND filename LIKE ", "filename LIKE ", True)
            query = f"SELECT *, 'files' as 'type' FROM files WHERE {substr}"
        elif search_type == 2:
            text_files = list(self.run_query(search))[:100]
            substr = get_sub_string(text_files, " OR filename = ")
            query = f"SELECT *, 'text' as 'type' FROM files WHERE {substr}"
        elif search_type == 3:
            query = "SELECT files.filename, size, creation, modification, 'files' as 'type' FROM files "
            query += "INNER JOIN image_objects on files.filename=image_objects.filename "
            query += "WHERE files.filename = image_objects.filename AND "
            arg_1 = " AND image_objects.objects LIKE "
            arg_2 = "image_objects.objects LIKE "
            query += get_sub_string(search.split(" "), arg_1, arg_2, True)
        elif search_type == 4:
            query = "SELECT files.filename, size, creation, modification, 'files' as 'type' FROM files "
            query += "INNER JOIN voices on files.filename=voices.filename "
            query += "WHERE files.filename = voices.filename AND "
            query += get_sub_string(search.split(" "), " AND voices.words LIKE ", "voices.words LIKE ", True)
        else:
            text_files = list(self.run_query(search))[:100]
            sub_query = get_sub_string(text_files, ' OR filename = ')
            query = "SELECT files.filename, files.size, files.creation, files.modification, ur.type as 'type' "
            query += "FROM files INNER JOIN ( "
            if sub_query:
                query += f"SELECT 'text' as type, filename, size FROM files WHERE {sub_query} "
                query += "UNION ALL "
            query += f"SELECT 'files' as type, filename, size FROM files WHERE filename LIKE '%{search}%' "
            query += "UNION ALL "
            query += f"SELECT 'images' as type, filename, objects FROM image_objects WHERE objects LIKE '%{search}%' "
            query += "UNION ALL "
            query += f"SELECT 'voices' as type, filename, words FROM voices WHERE words LIKE '%{search}%' "
            query += ") ur ON ur.filename=files.filename WHERE files.filename = ur.filename"
        return query

    def fill_treeview(self, widget):
        query = self.query_var.get()
        try:
            assert query, "Please enter a query string."
            query = self.get_query(query)
            widget.delete(*widget.get_children())
            assert not query.lower().endswith('where '), "No files were found."
            files = self.conn.cursor().execute(query).fetchall()
            assert len(files) > 0, f"'{self.query_var.get()}' related data not found."
            for index, row in enumerate(files):
                filename, size, creation, modification, table = row
                utc_create = self.epoch_to_date(creation)
                utc_mod = self.epoch_to_date(modification)
                widget.insert("", "end", values=(filename, table, int(size), utc_create, utc_mod))
        except AssertionError as error:
            self.message(error.args[0], "Info")
        except Exception as err:
            LOGGER.error(err)

    def open_target(self, event='file', widget=None, copy=False):
        try:
            cur_item = widget.focus()
            cur_text = widget.item(cur_item)['values'][0]
            target = cur_text if event == 'file' else str(Path(cur_text).parent)
            if copy:
                self.clipboard_clear()
                self.clipboard_append(target)
                self.update()
            else:
                os.startfile(target)
        except Exception as error:
            self.message(message=error.args[0])

    def folder_select(self, folder_list):
        answer = filedialog.askdirectory(parent=self, initialdir=os.environ['HOMEPATH'],
                                         title="Please select a folder:")
        folder_list.insert("end", str(Path(answer).absolute()))

    def destroy_active_frames(self):
        self.query_var.set('')
        self.search_type.set('1')
        self.indexer_type.set('1')
        if self.active_frames:
            for frame in self.active_frames: frame.destroy()

    def config_page(self):
        self.title('Configure Indexing')
        self.destroy_active_frames()
        config_file_frame = ttk.Frame(self)
        config_file_frame.columnconfigure(0, weight=16)
        config_file_frame.columnconfigure(1, weight=2)
        config_file_frame.columnconfigure(2, weight=16)
        frame_params = dict(column=0, sticky=tk.NSEW, padx=10)
        config_file_frame.grid(row=0, pady=(10, 10), **frame_params)

        grid_params = dict(row=0, sticky=tk.W)
        select_button = ttk.Button(config_file_frame, text='Include', width=71)
        select_button.grid(column=0, padx=(0, 5), **grid_params)
        exclude_button = ttk.Button(config_file_frame, text="Exclude", width=71, style='secondary.TButton')
        exclude_button.grid(column=2, **grid_params)

        config_radio_frame = ttk.LabelFrame(self, text='Configuration Parameters')
        config_radio_frame.grid(row=1, pady=(0, 0), ipady=5, **frame_params)

        grid_params = dict(row=2, sticky=tk.E)
        ttk.Label(config_radio_frame, text='Select Indexer: ').grid(column=0, **grid_params)
        radio_params = dict(variable=self.indexer_type, width=12)
        filename_indexer = ttk.Radiobutton(config_radio_frame, text='File Info', value=1, **radio_params)
        filename_indexer.grid(column=1, **grid_params)
        fulltext_indexer = ttk.Radiobutton(config_radio_frame, text='Full Text', value=2, **radio_params)
        fulltext_indexer.grid(column=2, **grid_params)
        radio_params['width'] = 17
        image_objects_indexer = ttk.Radiobutton(config_radio_frame, text='Image Labels', value=3, **radio_params)
        image_objects_indexer.grid(column=3, **grid_params)
        radio_params['width'] = 12
        audio_search_indexer = ttk.Radiobutton(config_radio_frame, text='Audio as Text', value=4, **radio_params)
        audio_search_indexer.grid(column=4, **grid_params)
        all_indexer = ttk.Radiobutton(config_radio_frame, text='All Indexers', value=5, **radio_params)
        all_indexer.grid(column=5, **grid_params)

        list_frame = ttk.Frame(self)
        list_frame.columnconfigure(0, weight=16)
        list_frame.columnconfigure(1, weight=2)
        list_frame.columnconfigure(2, weight=16)
        list_frame.grid(row=3, pady=(0, 10), **frame_params)

        ttk.Label(list_frame, text="Included Folders").grid(row=0, column=0, sticky=tk.W)
        list_box = tk.Listbox(list_frame, width=70, height=21, borderwidth=0, selectmode='multiple')
        list_box.grid(row=1, column=0, sticky=tk.EW)
        select_button.config(command=lambda widget=list_box: self.folder_select(folder_list=widget))
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
        action_frame.grid(row=4, pady=(0, 10), ipady=5, **frame_params)

        grid_params = dict(row=0, sticky=tk.E)
        delete_button = ttk.Button(action_frame, text='Delete', width=15, style='danger.TButton')
        command = dict(command=lambda _incl=list_box, _excl=list_box_excluded: self.remove_item(_incl, _excl))
        delete_button.config(**command)
        delete_button.grid(column=1, **grid_params)
        save_button = ttk.Button(action_frame, text='Save', width=15)
        command = dict(command=lambda _incl=list_box, _excl=list_box_excluded: self.save_config(_incl, _excl))
        save_button.config(**command)
        save_button.grid(column=2, **grid_params)
        indexer_button = ttk.Button(action_frame, text='Start Indexing', width=15, style='success.TButton')
        indexer_button.config(command=self.start_indexing)
        indexer_button.grid(column=3, **grid_params)
        stop_indexer_button = ttk.Button(action_frame, text='Stop Indexing', style='danger.TButton')
        stop_indexer_button.config(command=self.stop_indexing)
        stop_indexer_button.grid(column=4, **grid_params)

        self.read_config(list_box, list_box_excluded)
        self.active_frames = (config_file_frame, config_radio_frame, list_frame, action_frame)

    def do_popup(self, event, popup):
        try:
            popup.tk_popup(event.x_root, event.y_root)
        finally:
            popup.grab_release()

    def home_page(self):
        self.destroy_active_frames()
        self.title('AH Disk Search')
        query_frame = ttk.Frame(self)
        query_frame.columnconfigure(0, weight=1)
        query_frame.columnconfigure(1, weight=17)
        query_frame.columnconfigure(2, weight=1)
        query_frame.columnconfigure(3, weight=2)
        frame_params = dict(column=0, sticky=tk.NSEW, padx=10)
        query_frame.grid(row=0, pady=(15, 10), **frame_params)

        label = ttk.Label(query_frame, text='Search: ')
        label.grid(column=0, row=0, sticky=tk.W)
        
        query_entry = ttk.Entry(query_frame, textvariable=self.query_var, width=114, style='TEntry')
        self.query_entry = query_entry
        query_entry.focus()
        query_entry.grid(column=1, row=0, sticky=tk.EW)
        search_button = ttk.Button(query_frame, text='Search', width=20)
        search_button.grid(column=2, row=0, sticky=tk.W, padx=(5, 0))

        radio_frame = ttk.LabelFrame(self, text='Parameters')
        radio_frame.grid(row=1, ipady=5, **frame_params)

        grid_params = dict(row=2, sticky=tk.W)
        ttk.Label(radio_frame, text='Search type: ').grid(column=0, **grid_params)
        radio_params = dict(variable=self.search_type, width=10)
        filename = ttk.Radiobutton(radio_frame, text='Filename', value=1, **radio_params)
        filename.grid(column=1, **grid_params)
        fulltext = ttk.Radiobutton(radio_frame, text='Full Text', value=2, **radio_params)
        fulltext.grid(column=2, **grid_params)
        radio_params['width'] = 13
        image_objects = ttk.Radiobutton(radio_frame, text='Image Labels', value=3, **radio_params)
        image_objects.grid(column=3, **grid_params)
        audio_search = ttk.Radiobutton(radio_frame, text='Audio as Text', value=4, **radio_params)
        audio_search.grid(column=4, **grid_params)

        all_search = ttk.Radiobutton(radio_frame, text='All', value=5, **radio_params)
        all_search.grid(column=5, **grid_params)

        preview_list_frame = ttk.Frame(self)
        preview_list_frame.columnconfigure(0, weight=200)
        preview_list_frame.columnconfigure(2, weight=4)
        preview_list_frame.grid(row=4, pady=(0, 10), **frame_params)

        self.dock_viewer = DocViewer(preview_list_frame, width=100, scrollbars='horizontal')
        self.dock_viewer.fit_page(2.9)
        self.dock_viewer.grid(row=0, column=2, sticky=tk.NSEW)

        params = dict(columns=self.list_box_cols, show='headings', height=19)
        list_box = ttk.Treeview(preview_list_frame, **params)
        list_box.grid(row=0, column=0, sticky=tk.EW)
        scrollbar = ttk.Scrollbar(preview_list_frame, orient="vertical", command=list_box.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        list_box.configure(yscrollcommand=scrollbar.set)

        def tree_view_sort_column(col, reverse):
            items = [(list_box.set(k, col), k) for k in list_box.get_children('')]
            items.sort(key=lambda item: item[0], reverse=reverse)
            for index, (val, k) in enumerate(items):
                list_box.move(k, '', index)
            list_box.heading(col, text=col, command=lambda _col=col: tree_view_sort_column(_col, not reverse))

        for column in self.list_box_cols:
            list_box.column(column, minwidth=60, width=100)
            list_box.heading(column, text=column, command=lambda _col=column: tree_view_sort_column(_col, False))

        list_box.column('Filename', width=370)
        list_box.column('Module', width=50)
        list_box.column('Size', width=90)
        list_box.column('Created', width=115)
        list_box.column('Modified', width=115)
        list_box.bind("<<TreeviewSelect>>", lambda event, widget=list_box: self.file_preview(widget=widget))
        search_button.config(command=lambda widget=list_box: self.fill_treeview(widget=widget))
        popup = tk.Menu(self, tearoff=0)
        command = dict(command=lambda _event='file', widget=list_box: self.open_target(_event, widget, True))
        popup.add_command(label="Copy full path", **command)
        command = dict(command=lambda _event='folder', widget=list_box: self.open_target(_event, widget, True))
        popup.add_command(label="Copy folder location", **command)
        popup.add_separator()
        command = dict(command=lambda _event='file', widget=list_box: self.open_target(_event, widget))
        popup.add_command(label="Open file", **command)
        command = dict(command=lambda _event='folder', widget=list_box: self.open_target(_event, widget))
        popup.add_command(label="Open folder", **command)
        list_box.bind("<Double-1>", lambda event, _event='file', widget=list_box: self.open_target(_event, widget))
        list_box.bind("<Button-3>", lambda event, _popup=popup: self.do_popup(event, _popup))
        self.bind('<Return>', lambda event, widget=list_box: self.fill_treeview(widget=widget))
        self.show_hide_preview(widget=list_box)
        self.active_frames = (query_frame, radio_frame, preview_list_frame)

    def update_settings(self):
        data = read_path_config()
        data['hot_key'] = self.hot_key.get()
        data['file_size'] = self.file_size.get()
        data['preview'] = self.show_preview.get()
        keyboard.unhook_all_hotkeys()
        keyboard.add_hotkey(data['hot_key'], self.find_window_movetop, args=())
        self.write_config(json.dumps(data, indent=4))

    def settings_page(self):
        self.destroy_active_frames()
        self.title('Settings')
        settings_frame = ttk.Frame(self)
        settings_frame.columnconfigure(0, weight=1)
        settings_frame.columnconfigure(1, weight=16)
        settings_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=10, pady=30)

        ttk.Label(settings_frame, text='Hot Key: ').grid(row=0, column=0, sticky=tk.W)
        hot_key_entry = ttk.Entry(settings_frame, textvariable=self.hot_key, width=131)
        hot_key_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)

        ttk.Label(settings_frame, text='Max. file size(MB):').grid(row=1, column=0, sticky=tk.W)
        file_size_entry = ttk.Entry(settings_frame, textvariable=self.file_size)
        file_size_entry.grid(row=1, column=1, sticky=tk.EW)

        preview_show_hide = ttk.Checkbutton(
            settings_frame,
            text='Show/Hide Preview Pane',
            onvalue='show',
            offvalue='hide',
            variable=self.show_preview
        )
        preview_show_hide.config(command=self.update_settings)
        preview_show_hide.grid(row=2, column=1, sticky=tk.EW, pady=5)

        action_frame = ttk.Frame(self)
        action_frame.columnconfigure(0, weight=16)
        action_frame.grid(row=4, column=0, sticky=tk.NSEW, padx=10, pady=(0, 10))
        entry_update_button = ttk.Button(action_frame, text='Save', style='success.TButton')
        entry_update_button.config(command=self.update_settings)
        entry_update_button.grid(row=0, column=0, sticky=tk.EW)

        self.active_frames = [settings_frame, action_frame]


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
