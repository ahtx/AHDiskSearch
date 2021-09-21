import os
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, Tk
from ttkbootstrap import Style


class IndexerConfig:
    def __init__(self, master, style_theme):

        self.master = master
        root = tk.Toplevel(master)
        self.root = root
        # root.eval('tk::PlaceWindow . center')

        root.geometry("475x335")
        root.iconbitmap("ahsearch.ico")
        root.resizable(False, False)
        root.title("Indexer Configuration")

        lf = ttk.Labelframe(root, text='Parameters', padding=(5, 15, 15, 5))
        lf.pack(side='top', fill='x')

        # empty_label= tk.Label(lf,
        #                        width=10, 
        #                        text=" ", 
        #                        font=("Arial",10))
        # empty_label.grid(row=1, columnspan=3, sticky=tk.W)

        folder_label = tk.Label(lf,
                                width=10,
                                text="Folder: ",
                                font=("Arial", 10))
        folder_label.grid(row=2, column=1, sticky=tk.W)

        folder_name = tk.Entry(lf, width=40)
        folder_name.grid(row=2, column=2, sticky=tk.W)

        empty_label2 = tk.Label(lf,
                                width=10,
                                text=" ",
                                font=("Arial", 10))
        empty_label2.grid(row=3, columnspan=3, sticky=tk.W)

        self.folder_list = tk.Listbox(lf, width=52, height=10)
        self.folder_list.grid(row=3, column=1, columnspan=3, sticky=tk.EW, pady=(5, 0), padx=(15, 5))

        folder_button = ttk.Button(lf,
                                   text="Select",
                                   width=6,
                                   command=self.fsel,
                                   style='primary.TButton')
        folder_button.grid(row=2, column=3, sticky=tk.W, padx=(10, 5))

        del_button = ttk.Button(lf,
                                text="Delete",
                                width=6,
                                command=self.remove_item,
                                style='primary.TButton')
        del_button.grid(row=4, column=1, sticky=tk.S, padx=(10, 0), pady=(10, 0))

        save_button = ttk.Button(lf,
                                 text="Save",
                                 width=6,
                                 command=self.save_config,
                                 style='primary.TButton')
        save_button.grid(row=4, column=2, sticky=tk.S, pady=(10, 0))

        cancel_button = ttk.Button(lf,
                                   text="Cancel",
                                   width=6,
                                   command=self.exit,
                                   style='secondary.TButton')
        cancel_button.grid(row=4, column=3, sticky=tk.S, padx=(5, 0), pady=(10, 0))

        indexer_button = ttk.Button(root,
                                    text="Run Indexer",
                                    width=20,
                                    command=self.run_indexer,
                                    style='warning.TButton')
        # indexer_button.grid(row=5, column=1, columnspan=3, sticky=tk.S, padx=(50,50), pady=(10,0))
        indexer_button.pack(fill='both', pady=5, padx=15)

        try:
            self.read_config()
        except:
            pass

    def fsel(self):
        answer = filedialog.askdirectory(parent=self.root,
                                         initialdir=os.getcwd(),
                                         title="Please select a folder:")
        self.folder_list.insert("end", answer)

    def remove_item(self):
        for i in self.folder_list.curselection():
            self.folder_list.delete(i)

    def save_config(self):
        f = open("ahsearch.config", "w")
        for i in range(self.folder_list.size()):
            f.write(self.folder_list.get(i))
            f.write("\n")
        f.close()

    def read_config(self):
        f = open("ahsearch.config", "r")
        for l in f.readlines():
            l = l.strip("\n")
            self.folder_list.insert("end", l)
        f.close()

    def run_indexer(self):
        console = ['cmd.exe', '/c']
        cmd = ['python', 'AHDiskIndexer.py']
        subprocess.Popen(console + cmd)

    def exit(self):
        self.master.deiconify()
        self.root.destroy()
