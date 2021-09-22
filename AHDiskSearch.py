import os
import tkinter as tk
from functools import reduce
from pathlib import Path
from tkinter import ttk, messagebox
import pandas as pd
import sqlite3
import datetime
import sys
from ttkbootstrap import Style
from IndexerConfig import IndexerConfig
from AHFTSearch import FullTextSearch


def treeview_sort_column(tv, col, reverse):
    items = [(tv.set(k, col), k) for k in tv.get_children('')]
    items.sort(reverse=reverse)

    # rearrange items in sorted positions
    for index, (val, k) in enumerate(items):
        tv.move(k, '', index)

    # reverse sort next time
    tv.heading(col, text=col, command=lambda _col=col: treeview_sort_column(tv, _col, not reverse))


def message(message, name="showerror"):
    messagebox.showerror(name, message)


def create_connection():
    conn = None
    try:
        db_file = os.path.join(os.getcwd(), "filesystem.db")
        conn = sqlite3.connect(db_file)
    except Exception as e:
        print(e)

    return (conn)


def do_popup(event):
    try:
        menu.tk_popup(event.x_root, event.y_root)
    finally:
        menu.grab_release()


def get_sub_string(data: list, query_append, prefix='filename = ', like_query=False):
    try:
        assert data, 'Not found'
        result = reduce(lambda x, y: x.replace("'", "''") + f"{query_append}" + y.replace("'", "''"), data)
        return prefix + f'{query_append}'.join(
            f"'%{word}%'" if like_query else f"'{word}'" for word in result.split(f'{query_append}'))
    except:
        return ""


def show(e=""):
    tq = searchInput.get()
    sstring = ""
    if (imgobj.get() == 1):
        qu = f"""select files.filename, files.size, files.creation, files.modification from 
                        files 
                        INNER JOIN image_objects on files.filename=image_objects.filename
                    where 
                        files.filename = image_objects.filename AND """
        for w in tq.split(" "):
            sstring += f"image_objects.objects LIKE '%{w}%' AND "
        sstring = sstring[:-4]
    elif (imgobj.get() == 3):
        text_files = list(fts.run_query(tq))[:100]
        sstring = get_sub_string(text_files, " OR filename = ")
        qu = """SELECT * FROM files WHERE """
    else:
        sstring = get_sub_string(tq.split(" "), " AND filename LIKE ", "filename LIKE ", True)
        qu = """SELECT * FROM files WHERE """

    try:
        listBox.delete(*listBox.get_children())
    except Exception as e:
        print("Listbox delete failure")

    try:
        query = f"{qu}{sstring}"
        df = pd.read_sql_query(query, conn)
        for index, row in df.iterrows():
            UTC_create = datetime.datetime.utcfromtimestamp(row['creation'])
            UTC_mod = datetime.datetime.utcfromtimestamp(row['modification'])
            listBox.insert("", "end", values=(row['filename'], int(row['size']), UTC_create, UTC_mod))
    except:
        e = sys.exc_info()[0]
        print(f"SQL Error {e}")


def grab_full_path():
    curItem = listBox.focus()
    cur_text = listBox.item(curItem)['values'][0]
    search.clipboard_clear()
    search.clipboard_append(cur_text)
    search.update()


def grab_folder_path():
    curItem = listBox.focus()
    path = str(Path(listBox.item(curItem)['values'][0]).parent)
    search.clipboard_clear()
    search.clipboard_append(path)
    search.update()


def double_click_open(event):
    try:
        curItem = listBox.focus()
        cur_text = listBox.item(curItem)['values'][0]
        os.startfile(cur_text)
    except Exception as error:
        message(message=error.args[0])


def open_in_explorer():
    curItem = listBox.focus()
    path = str(Path(listBox.item(curItem)['values'][0]).parent)
    os.system(f"explorer {path}")


def iconfig():
    ic = IndexerConfig(search, style_theme)


def load_file():
    curItem = listBox.focus()
    cur_text = listBox.item(curItem)['values'][0]
    os.startfile(cur_text)


if __name__ == '__main__':
    photo_button = ttk.Radiobutton()
    imgobj = tk.IntVar()
    style_theme = "cosmo"
    style = Style(theme=style_theme)

    fts = FullTextSearch()

    conn = create_connection()
    search = style.master

    search.geometry("1025x510")
    # search.eval('tk::PlaceWindow . center')
    search.iconbitmap("ahsearch.ico")
    search.resizable(False, False)
    search.title("AH Desktop Search")

    search.columnconfigure(0, weight=1)
    search.columnconfigure(1, weight=10)
    search.columnconfigure(2, weight=1)
    search.columnconfigure(3, weight=1)
    search.columnconfigure(4, weight=1)
    params = dict(width=1, text=" ", font=("Arial", 10))
    emptyLabel2 = tk.Label(search, **params).grid(row=1, columnspan=6, sticky=tk.EW)
    params['text'] = "Query: "
    searchLabel = tk.Label(search, **params).grid(row=2, column=0, sticky=tk.EW)
    searchInput = tk.Entry(search, width=1)
    searchInput.grid(row=2, column=1, sticky=tk.EW, padx=(5, 0))
    params = dict(text="Search", width=1, command=show, style='primary.TButton')
    searchButton = ttk.Button(search, **params).grid(row=2, column=2, sticky=tk.EW, padx=(10, 1))
    params = dict(text="Config", width=1, command=iconfig, style='primary.TButton')
    configButton = ttk.Button(search, **params).grid(row=2, column=3, sticky=tk.EW, padx=(1, 1))
    params = dict(text="Exit", width=1, command=exit, style='secondary.TButton')
    exitButton = ttk.Button(search, **params).grid(row=2, column=4, sticky=tk.EW, padx=(1, 1))

    lf = ttk.Labelframe(search, text='Parameters', padding=(5, 5, 5, 5))
    photo_label = ttk.Label(lf, width=15, text="Search type: ", font=("Arial", 10)).pack(side="left")
    photo_button1 = ttk.Radiobutton(lf, width=15, text="Image Objects", variable=imgobj, value=1).pack(side='left')
    photo_button2 = ttk.Radiobutton(lf, width=12, text="Filenames", variable=imgobj, value=2).pack(side='left')
    photo_button3 = ttk.Radiobutton(lf, width=15, text="Full Text", variable=imgobj, value=3).pack(side='left')
    lf.grid(row=3, column=0, columnspan=6, sticky=tk.EW)
    search.bind('<Return>', show)

    menu = tk.Menu(search, tearoff=0)
    menu.add_command(label="Copy full path", command=grab_full_path)
    menu.add_command(label="Copy folder location", command=grab_folder_path)
    menu.add_separator()
    menu.add_command(label="Open file", command=load_file)
    menu.add_command(label="Open folder", command=open_in_explorer)

    # create Treeview with 3 columns
    cols = ('Filename', 'Size', 'Created', 'Modified')
    style.configure("cosmo.Treeview", highlightthickness=0, bd=0, font=('Calibri', 8))  # Modify the font of the body
    style.configure("cosmo.Treeview.Heading", font=('Calibri', 10))  # Modify the font of the headings
    listBox = ttk.Treeview(search, style="cosmo.Treeview", columns=cols, show='headings', height=20)
    vsb = ttk.Scrollbar(orient="vertical", command=listBox.yview)
    vsb.grid(row=4, column=5, sticky='ns')

    listBox.configure(yscrollcommand=vsb.set)
    # set column headings
    for col in cols:
        # listBox.heading(col, text=col)
        listBox.column(col, minwidth=150, width=250)

        listBox.heading(col, text=col, command=lambda _col=col: treeview_sort_column(listBox, _col, False))
    listBox.column('Filename', minwidth=250, width=650)
    listBox.column('Size', minwidth=50, width=150)
    listBox.column('Created', minwidth=100, width=100)
    listBox.column('Modified', minwidth=100, width=100)
    listBox.grid(row=4, column=0, columnspan=5)

    listBox.bind("<Button-3>", do_popup)
    listBox.bind("<Double-1>", double_click_open)

    search.mainloop()
