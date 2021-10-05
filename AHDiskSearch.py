import os
from sys import exit, path
import tkinter as tk
from functools import reduce
from pathlib import Path
from tkinter import ttk, messagebox
import datetime
from ttkbootstrap import Style
from IndexerConfig import IndexerConfig
from AHFTSearch import FullTextSearch

path.append(os.path.join(os.path.dirname(__file__), '..'))
from dist.shared import create_connection, BASE_DIR, LOGGER


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
        LOGGER.warning(error)
        return ""


def get_query(tq):
    if imgobj.get() == 1:
        query = "SELECT files.filename, files.size, files.creation, files.modification FROM files "
        query += "INNER JOIN image_objects on files.filename=image_objects.filename "
        query += "WHERE files.filename = image_objects.filename AND "
        query += get_sub_string(tq.split(" "), " AND image_objects.objects LIKE ", "image_objects.objects LIKE ", True)
    elif imgobj.get() == 4:
        query = "SELECT files.filename, files.size, files.creation, files.modification FROM files "
        query += "INNER JOIN voices on files.filename=voices.filename "
        query += "WHERE files.filename = voices.filename AND "
        query += get_sub_string(tq.split(" "), " AND voices.words LIKE ", "voices.words LIKE ", True)
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
        assert tq, "Please enter a query!"
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
    except Exception as err:
        LOGGER.error(err)


def grab_full_path():
    try:
        cur_item = list_box.focus()
        cur_text = list_box.item(cur_item)['values'][0]
        search.clipboard_clear()
        search.clipboard_append(cur_text)
        search.update()
    except:
        pass


def grab_folder_path():
    cur_item = list_box.focus()
    folder_path = str(Path(list_box.item(cur_item)['values'][0]).parent)
    search.clipboard_clear()
    search.clipboard_append(folder_path)
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
    folder_path = str(Path(list_box.item(cur_item)['values'][0]).parent)
    os.system(f"explorer {folder_path}")


def iconfig():
    ic = IndexerConfig(search, style)


def load_file():
    cur_item = list_box.focus()
    cur_text = list_box.item(cur_item)['values'][0]
    os.startfile(cur_text)


def create_tables():
    tables = dict(
        files="(filename TEXT PRIMARY KEY, size BIGINT, creation DATETIME, modification DATETIME)",
        image_objects="(filename TEXT PRIMARY KEY, objects TEXT, probabilities TEXT)",
        voices="(filename TEXT PRIMARY KEY, words TEXT)"
    )
    for table in ('files', 'image_objects', 'voices'):
        query = f"CREATE TABLE {table} {tables[table]};"
        try:
            conn.cursor().execute(query)
        except Exception as error:
            LOGGER.warning(error)


if __name__ == '__main__':
    search = tk.Tk()
    imgobj = tk.IntVar()
    imgobj.set(2)
    style_theme = "cosmo"
    style = Style(theme=style_theme)
    highlight_color = '#64ed71'
    style.configure(
        'TButton',
        borderwidth=3,
    )
    style.map('primary.TButton', bordercolor=[('focus', highlight_color)])
    style.map('secondary.TButton', bordercolor=[('focus', highlight_color)])
    style.map('warning.TButton', bordercolor=[('focus', highlight_color)])
    style.map('BW.TRadiobutton', foreground=[('focus', highlight_color)])
    style.map('Treeview', bordercolor=[('focus', highlight_color)])

    fts = FullTextSearch()

    conn = create_connection()
    create_tables()
    search.style = style.master

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
    search.bind('<Return>', show)
    search.bind('<Control-x>', lambda event: search.destroy())
    search.bind('<Control-c>', lambda event: grab_full_path())
    search.bind('<Control-s>', lambda event: iconfig())

    params = dict(width=1, text=" ", font=("Arial", 10))
    # emptyLabel2 = tk.Label(search, **params).grid(row=1, columnspan=6, sticky=tk.EW)
    params['text'] = "Query: "
    params['font'] = ("Arial", 10, "bold")
    search_label = tk.Label(search, **params).grid(row=2, column=0, sticky=tk.EW)
    search_value = tk.StringVar()
    search_input = tk.Entry(search, width=1, textvariable=search_value, highlightcolor=highlight_color)
    search_input.grid(row=2, column=1, sticky=tk.EW, ipady=4, padx=(5, 0))
    search.bind('<Control-q>', lambda event: search_input.focus())
    search_input.focus()

    params = dict(text="Search", width=1, command=show, style='primary.TButton')
    search_button = ttk.Button(search, **params).grid(row=2, column=2, sticky=tk.EW, padx=(10, 1))
    params = dict(text="Config", width=1, command=iconfig, style='primary.TButton')
    config_button = ttk.Button(search, **params).grid(row=2, column=3, sticky=tk.EW, padx=(1, 1))
    params = dict(text="Exit", width=1, command=exit, style='secondary.TButton')
    exit_button = ttk.Button(search, **params).grid(row=2, column=4, sticky=tk.EW, padx=(1, 1))

    lf = ttk.Labelframe(search, text='Parameters', padding=(5, 5, 5, 5))
    lf.grid(row=3, column=0, columnspan=6, sticky=tk.EW)
    params = dict(style='BW.TRadiobutton', variable=imgobj)
    photo_label = ttk.Label(lf, width=15, text="Search type: ", font=("Arial", 10, "bold")).pack(side="left")
    photo_button2 = ttk.Radiobutton(lf, width=12, text="Filenames", value=2, **params).pack(side='left')
    photo_button3 = ttk.Radiobutton(lf, width=15, text="Full Text", value=3, **params).pack(side='left')
    photo_button1 = ttk.Radiobutton(lf, width=15, text="Image Objects", value=1, **params).pack(side='left')
    photo_button4 = ttk.Radiobutton(lf, width=15, text="Audio/Video to Text", value=4, **params).pack(side='left')

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
