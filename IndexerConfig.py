import os
import subprocess
import tkinter as tk
from collections import namedtuple
from tkinter import ttk, filedialog

from dist.shared import BASE_DIR


Indexer = namedtuple('Indexer', ['disk', 'fulltext', 'image'])


class IndexerConfig:
    def __init__(self, master, style_theme):

        self.master = master
        root = tk.Toplevel(master)
        self.root = root
        self.config_file = os.path.join(BASE_DIR, 'dist', 'ahsearch.config')
        root.geometry("500x390")
        icon_file = os.path.join(BASE_DIR, 'dist', 'ahsearch.ico')
        root.iconbitmap(icon_file)
        root.resizable(False, False)
        root.title("Indexer Configuration")

        self.indexer = Indexer(*['Disk Indexer', 'Full Text Indexer', 'Object Detector'])

        self.indexer_obj = tk.StringVar()
        self.indexer_obj.set(self.indexer.disk)

        indexer_frame = ttk.LabelFrame(root, text='Parameters', padding=(5, 15, 15, 5))
        indexer_frame.pack(side='top', fill=tk.BOTH, padx=10, pady=(10, 0))

        font_arial_10 = ("Arial", 10, "bold")
        params = dict(width=10, text="Folder: ", font=font_arial_10)
        folder_label = tk.Label(indexer_frame, **params)
        folder_label.grid(row=0, column=0, sticky=tk.W)

        folder_name = tk.Entry(indexer_frame)
        folder_name.grid(row=0, column=1, columnspan=2, ipady=4, sticky=tk.EW)
        folder_name.focus()

        folder_button = ttk.Button(indexer_frame, text="Select", width=6, command=self.fsel, style='primary.TButton')
        folder_button.grid(row=0, column=3, sticky=tk.EW)

        indexer_label = ttk.Label(indexer_frame, width=15, text="Select Indexer: ", font=("Arial", 10, "bold"))
        indexer_label.grid(row=1, column=0, sticky=tk.EW, pady=10)
        disk_indexer = ttk.Radiobutton(indexer_frame, text="Disk Indexer", width=12, variable=self.indexer_obj, value=self.indexer.disk)
        disk_indexer.grid(row=1, column=1, sticky=tk.EW)
        fdisk_indexer = ttk.Radiobutton(indexer_frame, text="Full Disk Indexer", width=15, variable=self.indexer_obj, value=self.indexer.fulltext)
        fdisk_indexer.grid(row=1, column=2, sticky=tk.EW)
        object_indexer = ttk.Radiobutton(indexer_frame, text="Objects Indexer", width=15, variable=self.indexer_obj,  value=self.indexer.image)
        object_indexer.grid(row=1, column=3, sticky=tk.EW)

        lf = ttk.Frame(root)
        lf.pack(side='top', fill=tk.BOTH, padx=10, pady=(0, 10))

        self.folder_list = tk.Listbox(lf, height=10, width=68)
        self.folder_list.grid(row=0, column=0, columnspan=3, sticky=tk.EW, pady=10)

        del_button = ttk.Button(lf, text='Delete', command=self.remove_item)
        del_button.grid(row=1, column=0, sticky=tk.W)

        save_button = ttk.Button(lf, text='Save', command=self.save_config)
        save_button.grid(row=1, column=1, columnspan=1, sticky=tk.EW)

        cancel_button = ttk.Button(lf, text='Cancel', command=self.exit)
        cancel_button.grid(row=1, column=2, sticky=tk.E)

        params = {'text': 'Run Indexer', 'width': 20, 'command': self.run_indexer, 'style': 'warning.TButton'}
        indexer_button = ttk.Button(root, **params)
        indexer_button.pack(fill='both', padx=10)

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

        file = open(self.config_file, "w")
        for i in range(self.folder_list.size()):
            file.write(self.folder_list.get(i))
            file.write("\n")
        file.close()

    def read_config(self):
        file = open(self.config_file, "r")
        for line in file.readlines():
            line = line.strip("\n")
            self.folder_list.insert("end", line)
        file.close()

    def run_indexer(self):
        executeable = {
            'Disk Indexer': ('AHDiskIndexer.exe', 'AHDiskIndexer.py'),
            'Full Text Indexer': ('AHFullTextIndexer.exe', 'AHFullTextIndexer.py'),
            'Object Detector': ('AHObjectDetector.exe', 'AHObjectDetector.py')
        }
        target = os.path.join(BASE_DIR, 'dist', executeable[self.indexer_obj.get()][0])
        if os.path.exists(target):
            subprocess.Popen(f"{target}")
        else:
            console = ['cmd.exe', '/c']
            target = os.path.join(BASE_DIR, 'dist', executeable[self.indexer_obj.get()][1])
            cmd = ['python', f"{target}"]
            subprocess.Popen(console + cmd)


    def exit(self):
        self.master.deiconify()
        self.root.destroy()
