import logging
import os
from sys import exit
import tkinter as tk
from functools import reduce
from pathlib import Path
from tkinter import ttk, messagebox
import datetime
from ttkbootstrap import Style
from IndexerConfig import IndexerConfig
from AHFTSearch import FullTextSearch
from dist.shared import create_connection, BASE_DIR, LOGGER_TIME_FORMAT

log_file = os.path.join(BASE_DIR, 'dist', 'disk_seach.log')
logging.basicConfig(
    filename=log_file,
    filemode='w',
    format='%(asctime)s-%(levelname)s - %(message)s',
    datefmt=LOGGER_TIME_FORMAT
)


def treeview_sort_column(tv, col, reverse):
    items = [(tv.set(k, col), k) for k in tv.get_children('')]
    items.sort(reverse=reverse)

    # rearrange items in sorted positions
    for index, (val, k) in enumerate(items):
        tv.move(k, '', index)

    # reverse sort next time
    tv.heading(col, text=col, command=lambda _col=col: treeview_sort_column(tv, _col, not reverse))


def message(message, name="Error"):
    methods = dict(Error=messagebox.showerror, Info=messagebox.showinfo, Warning=messagebox.showwarning)
    methods[name](title=name, message=message)


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
    except Exception as error:
        return ""


def get_query(tq):
    if imgobj.get() == 1:
        query = "SELECT files.filename, files.size, files.creation, files.modification FROM files "
        query += "INNER JOIN image_objects on files.filename=image_objects.filename "
        query += "WHERE files.filename = image_objects.filename AND "
        query += get_sub_string(tq.split(" "), " AND image_objects.objects LIKE ", "image_objects.objects LIKE ", True)
    elif imgobj.get() == 3:
        text_files = list(fts.run_query(tq))[:100]
        query = "SELECT * FROM files WHERE "
        query += get_sub_string(text_files, " OR filename = ")
    else:
        query = "SELECT * FROM files WHERE "
        query += get_sub_string(tq.split(" "), " AND filename LIKE ", "filename LIKE ", True)
    return query


def show(e=""):
    tq = search_value.get()
    try:
        assert tq, "Please enter some query!"
        query = get_query(tq)
        list_box.delete(*list_box.get_children())
        assert not query.lower().endswith('where '), "Data not found!"
        files = conn.cursor().execute(query).fetchall()
        for index, row in enumerate(files):
            filename, size, creation, modification = row
            utc_create = datetime.datetime.utcfromtimestamp(creation)
            utc_mod = datetime.datetime.utcfromtimestamp(modification)
            list_box.insert("", "end", values=(filename, int(size), utc_create, utc_mod))
    except AssertionError as error:
        message(error.args[0], "Error")
    except Exception as error:
        logging.error(error)


def grab_full_path():
    cur_item = list_box.focus()
    cur_text = list_box.item(cur_item)['values'][0]
    search.clipboard_clear()
    search.clipboard_append(cur_text)
    search.update()


def grab_folder_path():
    cur_item = list_box.focus()
    path = str(Path(list_box.item(cur_item)['values'][0]).parent)
    search.clipboard_clear()
    search.clipboard_append(path)
    search.update()


def double_click_open(event):
    try:
        cur_item = list_box.focus()
        cur_text = list_box.item(cur_item)['values'][0]
        os.startfile(cur_text)
    except Exception as error:
        message(message=error.args[0])


def open_in_explorer():
    cur_item = list_box.focus()
    path = str(Path(list_box.item(cur_item)['values'][0]).parent)
    os.system(f"explorer {path}")


def iconfig():
    ic = IndexerConfig(search, style_theme)


def load_file():
    cur_item = list_box.focus()
    cur_text = list_box.item(cur_item)['values'][0]
    os.startfile(cur_text)


if __name__ == '__main__':
    photo_button = ttk.Radiobutton()
    imgobj = tk.IntVar()
    imgobj.set(2)
    style_theme = "cosmo"
    style = Style(theme=style_theme)

    fts = FullTextSearch()

    conn = create_connection()
    search = style.master

    search.geometry("1025x510")
    # search.eval('tk::PlaceWindow . center')
    icon_file = os.path.join(BASE_DIR, 'dist', 'ahsearch.ico')
    search.iconbitmap(icon_file)
    search.resizable(False, False)
    search.title("AH Desktop Search")

    search.columnconfigure(0, weight=1)
    search.columnconfigure(1, weight=10)
    search.columnconfigure(2, weight=1)
    search.columnconfigure(3, weight=1)
    search.columnconfigure(4, weight=1)
    params = dict(width=1, text=" ", font=("Arial", 10))
    # emptyLabel2 = tk.Label(search, **params).grid(row=1, columnspan=6, sticky=tk.EW)
    params['text'] = "Query: "
    params['font'] = ("Arial", 10, "bold")
    search_label = tk.Label(search, **params).grid(row=2, column=0, sticky=tk.EW)
    search_value = tk.StringVar()
    search_input = tk.Entry(search, width=1, textvariable=search_value)
    search_input.grid(row=2, column=1, sticky=tk.EW, ipady=4, padx=(5, 0))
    search_input.focus()
    params = dict(text="Search", width=1, command=show, style='primary.TButton')
    search_button = ttk.Button(search, **params).grid(row=2, column=2, sticky=tk.EW, padx=(10, 1))
    params = dict(text="Config", width=1, command=iconfig, style='primary.TButton')
    config_button = ttk.Button(search, **params).grid(row=2, column=3, sticky=tk.EW, padx=(1, 1))
    params = dict(text="Exit", width=1, command=exit, style='secondary.TButton')
    exit_button = ttk.Button(search, **params).grid(row=2, column=4, sticky=tk.EW, padx=(1, 1))

    lf = ttk.Labelframe(search, text='Parameters', padding=(5, 5, 5, 5))
    lf.grid(row=3, column=0, columnspan=6, sticky=tk.EW)
    photo_label = ttk.Label(lf, width=15, text="Search type: ", font=("Arial", 10, "bold")).pack(side="left")
    photo_button2 = ttk.Radiobutton(lf, width=12, text="Filenames", variable=imgobj, value=2).pack(side='left')
    photo_button3 = ttk.Radiobutton(lf, width=15, text="Full Text", variable=imgobj, value=3).pack(side='left')
    photo_button1 = ttk.Radiobutton(lf, width=15, text="Image Objects", variable=imgobj, value=1).pack(side='left')
    search.bind('<Return>', show)

    menu = tk.Menu(search, tearoff=0)
    menu.add_command(label="Copy full path", command=grab_full_path)
    menu.add_command(label="Copy folder location", command=grab_folder_path)
    menu.add_separator()
    menu.add_command(label="Open file", command=load_file)
    menu.add_command(label="Open folder", command=open_in_explorer)

    style_cosomo_treeview = "cosmo.Treeview"
    # create Treeview with 3 columns
    cols = ('Filename', 'Size', 'Created', 'Modified')
    style.configure(style_cosomo_treeview, highlightthickness=0, bd=0,
                    font=('Calibri', 8))  # Modify the font of the body
    style.configure(style_cosomo_treeview + ".Heading", font=('Calibri', 10))  # Modify the font of the headings
    list_box = ttk.Treeview(search, style=style_cosomo_treeview, columns=cols, show='headings', height=20)
    vsb = ttk.Scrollbar(orient="vertical", command=list_box.yview)
    vsb.grid(row=4, column=5, sticky='ns')

    list_box.configure(yscrollcommand=vsb.set)
    for col in cols:
        list_box.column(col, minwidth=150, width=250)

        list_box.heading(col, text=col, command=lambda _col=col: treeview_sort_column(list_box, _col, False))
    list_box.column('Filename', minwidth=250, width=650)
    list_box.column('Size', minwidth=50, width=150)
    list_box.column('Created', minwidth=100, width=100)
    list_box.column('Modified', minwidth=100, width=100)
    list_box.grid(row=4, column=0, columnspan=5)

    list_box.bind("<Button-3>", do_popup)
    list_box.bind("<Double-1>", double_click_open)
    list_box.bind("<Return>", double_click_open)

    search.mainloop()
