import os
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog


class IndexerConfig:
    def __init__(self, master, style_theme):

        self.master = master
        root = tk.Toplevel(master)
        self.root = root

        root.geometry("475x335")
        root.iconbitmap("ahsearch.ico")
        root.resizable(False, False)
        root.title("Indexer Configuration")

        lf = ttk.Labelframe(root, text='Parameters', padding=(5, 15, 15, 5))
        lf.pack(side='top', fill='x')
        font_arial_10 = ("Arial", 10)
        params = dict(width=10, text="Folder: ", font=font_arial_10)
        folder_label = tk.Label(lf, **params)
        folder_label.grid(row=2, column=1, sticky=tk.W)
        folder_name = tk.Entry(lf, width=40)
        folder_name.grid(row=2, column=2, sticky=tk.W)
        params.update({'text': ' '})
        empty_label2 = tk.Label(lf, **params)
        empty_label2.grid(row=3, columnspan=3, sticky=tk.W)
        self.folder_list = tk.Listbox(lf, width=52, height=10)
        self.folder_list.grid(row=3, column=1, columnspan=3, sticky=tk.EW, pady=(5, 0), padx=(15, 5))
        params = dict(text="Select", width=6, command=self.fsel, style='primary.TButton')
        folder_button = ttk.Button(lf, **params)
        folder_button.grid(row=2, column=3, sticky=tk.W, padx=(10, 5))
        params.update({'text': 'Delete', 'command': self.remove_item})
        del_button = ttk.Button(lf, **params)
        del_button.grid(row=4, column=1, sticky=tk.S, padx=(10, 0), pady=(10, 0))
        params.update({'text': 'Save', 'command': self.save_config})
        save_button = ttk.Button(lf, **params)
        save_button.grid(row=4, column=2, sticky=tk.S, pady=(10, 0))
        params.update({'text': 'Cancel', 'command': self.exit})
        cancel_button = ttk.Button(lf, **params)
        cancel_button.grid(row=4, column=3, sticky=tk.S, padx=(5, 0), pady=(10, 0))
        params.update({'text': 'Run Indexer', 'width': 20, 'command': self.exit, 'style': 'warning.TButton'})
        indexer_button = ttk.Button(root, **params)
        indexer_button.pack(fill='both', pady=5, padx=15)

        try:
            self.read_config()
        except:
            pass

    def fsel(self):
        answer = filedialog.askdirectory(parent=self.root, initialdir=os.getcwd(), title="Please select a folder:")
        self.folder_list.insert("end", answer)

    def remove_item(self):
        for i in self.folder_list.curselection():
            self.folder_list.delete(i)

    def save_config(self):
        file = open("ahsearch.config", "w")
        for i in range(self.folder_list.size()):
            file.write(self.folder_list.get(i))
            file.write("\n")
        file.close()

    def read_config(self):
        file = open("ahsearch.config", "r")
        for line in file.readlines():
            line = line.strip("\n")
            self.folder_list.insert("end", line)
        file.close()

    def run_indexer(self):
        console = ['cmd.exe', '/c']
        for file in ("AHDiskIndexer.py", "AHFullTextIndexer.py", "AHObjectDetector.py"):
            print(f"Indexing {file}")
            cmd = ['python', file]
            subprocess.Popen(console + cmd)

    def exit(self):
        self.master.deiconify()
        self.root.destroy()
