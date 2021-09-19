import os
import tkinter as tk
from tkinter import ttk, Tk
import pandas as pd
import sqlite3
import datetime
import sys
from ttkbootstrap import Style
from IndexerConfig import IndexerConfig
from AHFTSearch import FullTextSearch

photo_button = ttk.Radiobutton()
imgobj = tk.IntVar()
style_theme = "cosmo"
style = Style(theme=style_theme)

database = "filesystem.db"
fts = FullTextSearch()

def treeview_sort_column(tv, col, reverse):
    l = [(tv.set(k, col), k) for k in tv.get_children('')]
    l.sort(reverse=reverse)

    # rearrange items in sorted positions
    for index, (val, k) in enumerate(l):
        tv.move(k, '', index)

    # reverse sort next time
    tv.heading(col, text=col, command=lambda _col=col: \
                 treeview_sort_column(tv, _col, not reverse))

def create_connection(db_file):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
    except Error as e:
        print(e)

    return(conn)

def do_popup(event):
    try:
        m.tk_popup(event.x_root, event.y_root)
    finally:
        m.grab_release()



def show(e=""):
    
    tq = searchInput.get()
    sstring = ""
    qu = ""
    
    if(imgobj.get() == 1):
        qu = f"""select files.filename, files.size, files.creation, files.modification from 
                        files 
                        INNER JOIN image_objects on files.filename=image_objects.filename
                    where 
                        files.filename = image_objects.filename AND """
        for w in tq.split(" "):
            sstring = f"{sstring}image_objects.objects LIKE '%{w}%' AND "
        sstring = sstring[:-4]
    elif(imgobj.get() == 3):
        text_files = list(fts.run_query(tq))[:100]
        #print(list(text_files))
        for w in text_files:
            w = w.replace("'","''")
            sstring = f"{sstring}filename = '{w}' OR "
        sstring = sstring[:-4]
        qu = """SELECT * FROM files WHERE """
        #print(f"{qu}{sstring}")
    else:
        for w in tq.split(" "):
            sstring = f"{sstring}filename LIKE '%{w}%' AND "
        sstring = sstring[:-4]
        qu = """SELECT * FROM files WHERE """
    
    try: 
        df = pd.read_sql_query(f"{qu}{sstring}", conn)
    except:
        e = sys.exc_info()[0]
        print(f"SQL Error {e}")
        
    
    try: 
        listBox.delete(*listBox.get_children())
    except Exception as e:
        print("Listbox delete failure")
        print(e)
        pass

    for index, row in df.iterrows():
        UTC_create = datetime.datetime.utcfromtimestamp(row['creation'])
        UTC_mod = datetime.datetime.utcfromtimestamp(row['modification'])
        listBox.insert("","end",values=(row['filename'], int(row['size']), UTC_create, UTC_mod))        

def grab_full_path():
    cur_row = listBox.selection()
    for r in cur_row:
        cur_text = listBox.item(r)["values"][0]
    search.clipboard_clear()
    search.clipboard_append(cur_text)
    search.update()

def grab_folder_path():
    cur_row = listBox.selection()
    for r in cur_row:
        cur_text = os.path.dirname(listBox.item(r)["values"][0])
    search.clipboard_clear()
    search.clipboard_append(cur_text)
    search.update()

def open_in_explorer():
    cur_row = listBox.selection()
    for r in cur_row:
        cur_text = os.path.dirname(listBox.item(r)["values"][0])
    os.system(f"explorer {cur_text}")

def iconfig():
    ic = IndexerConfig(search,style_theme)

def load_file():
    cur_row = listBox.selection()
    for r in cur_row:
        cur_text = listBox.item(r)["values"][0]
    os.system(f"explorer \"{cur_text}\"")

conn = create_connection(database)
#search = tk.Tk()
search = style.master


search.geometry("1025x510")
#search.eval('tk::PlaceWindow . center')
search.iconbitmap("ahsearch.ico")
search.resizable(False, False)
search.title("AH Desktop Search")
#label = tk.Label(search, text="Desktop Search", font=("Arial",14)).grid(row=0, column=0, columnspan=5)

search.columnconfigure(0, weight=1)
search.columnconfigure(1, weight=10)
search.columnconfigure(2, weight=1)
search.columnconfigure(3, weight=1)
search.columnconfigure(4, weight=1)

emptyLabel2 = tk.Label(search, width=1, text=" ", font=("Arial",10)).grid(row=1, columnspan=6, sticky=tk.EW)
searchLabel = tk.Label(search, width=1, text="Query: ", font=("Arial",10)).grid(row=2, column=0, sticky=tk.EW)
searchInput = tk.Entry(search, width=1)
searchInput.grid(row=2, column=1, sticky=tk.EW, padx=(5,0))
searchButton = ttk.Button(search, text="Search", width=1, command=show, style='primary.TButton').grid(row=2, column=2, sticky=tk.EW, padx=(10,1))
configButton = ttk.Button(search, text="Config", width=1, command=iconfig, style='primary.TButton').grid(row=2, column=3, sticky=tk.EW, padx=(1,1))
exitButton = ttk.Button(search, text="Exit", width=1, command=exit, style='secondary.TButton').grid(row=2, column=4, sticky=tk.EW, padx=(1,1))

lf = ttk.Labelframe(search, text='Parameters', padding=(5, 5, 5, 5))
photo_label = ttk.Label(lf, width=15, text="Search type: ", font=("Arial",10)).pack(side="left")
photo_button = ttk.Radiobutton(lf, width=15, text="Image Objects", variable=imgobj, value=1).pack(side='left')
photo_button2 = ttk.Radiobutton(lf, width=12, text="Filenames", variable=imgobj, value=2).pack(side='left')
photo_button3 = ttk.Radiobutton(lf, width=15, text="Full Text", variable=imgobj, value=3).pack(side='left')
lf.grid(row=3,column=0,columnspan=6,sticky=tk.EW)
search.bind('<Return>', show)

m = tk.Menu(search, tearoff = 0)
m.add_command(label ="Copy full path",command=grab_full_path)
m.add_command(label ="Copy folder location",command=grab_folder_path)
m.add_separator()
m.add_command(label ="Open file",command=load_file)
m.add_command(label ="Open folder",command=open_in_explorer)

# create Treeview with 3 columns
cols = ('Filename', 'Size', 'Created', 'Modified')
style.configure("cosmo.Treeview", highlightthickness=0, bd=0, font=('Calibri', 8)) # Modify the font of the body
style.configure("cosmo.Treeview.Heading", font=('Calibri', 10)) # Modify the font of the headings
listBox = ttk.Treeview(search, style="cosmo.Treeview",columns=cols, show='headings', height=20)
vsb = ttk.Scrollbar(orient="vertical",command=listBox.yview)
vsb.grid(row=4, column=5,sticky='ns')

listBox.configure(yscrollcommand=vsb.set)
# set column headings
for col in cols:
    #listBox.heading(col, text=col)
    listBox.column(col,minwidth=150,width=250)
    
    listBox.heading(col, text=col, command=lambda _col=col: \
                     treeview_sort_column(listBox, _col, False))
listBox.column('Filename',minwidth=250,width=650)
listBox.column('Size',minwidth=50,width=150)
listBox.column('Created',minwidth=100,width=100)
listBox.column('Modified',minwidth=100,width=100)
listBox.grid(row=4, column=0, columnspan=5)

listBox.bind("<Button-3>", do_popup)

search.mainloop()