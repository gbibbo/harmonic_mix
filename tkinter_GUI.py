import tkinter as tk
from tkinter import ttk
from tkinter import *
from tkinter import filedialog as fd
from tkinter.constants import DISABLED, NORMAL
import os
import ntpath
from os import walk
from main import compare_songs, analyze_song

folderpath = ''  # <---container

# this is the function called when the button is clicked
def music_button():
	global folderpath
	folderpath = fd.askdirectory()
	text1.configure(text=folderpath[0:75])
	text2.configure(text=folderpath[75:])
	text3.configure(text="")
	text4.configure(text="")
	e.delete(*e.get_children())
	row = 0
	for (dirpath, dirnames, filenames) in walk(folderpath):
		for file in filenames:
			e.insert('', 'end', values=(file.replace(".mp3", ""),
										'',
										'',
										''))
			row = row + 1
		break

	print(folderpath)

def main_song_selected(event):
	print(e.index(e.focus()))
	global folderpath
	row = 0
	for (dirpath, dirnames, filenames) in walk(folderpath):
		for file in filenames:
			if row == e.index(e.focus()):
				current_song = file.replace(".mp3", "")
			row = row + 1
		break
	text3.configure(text=current_song[0:36])
	text4.configure(text=current_song[36:])

	current_song_path = folderpath + '/' + current_song + ".mp3"

	folder_path, song_name = ntpath.split(current_song_path)
	annotation_path = folder_path + '/annotations/' + song_name.replace(".mp3", ".json")
	if os.path.isfile(annotation_path):
		e.delete(*e.get_children())
		row = 0
		# Compute harmonic compatibility
		for (dirpath, dirnames, filenames) in walk(folderpath):
			for file in filenames:
				candidate_song_path = dirpath + '/' + file
				harmonic_compatibility, pitch_shift, min_small_scale_comp = compare_songs(current_song_path,
																						  candidate_song_path)
				e.insert('', 'end', values=(file.replace(".mp3", ""),
											str(round(harmonic_compatibility, 1)),
											'  ' + str(pitch_shift),
											str(round(min_small_scale_comp, 1))))
				row = row + 1
			break
	else:
		text3.configure(text="You need to analyze first")
		text4.configure(text="")
		return

# this is the function called when the button is clicked
def analyze_button():
	text3.configure(text="Analyzing...")
	text4.configure(text="")
	global folderpath
	i = 0
	for (dirpath, dirnames, filenames) in walk(folderpath):
		for file in filenames:
			song_path = dirpath + '/' + file
			analyze_song(song_path)
			i = i + 1
			text3.configure(text=str(round(i * 100 / len(filenames), 1)) + '% progress completed')
			print(round(i * 100 / len(filenames), 1), '% progress completed')
		break
	text3.configure(text="Analysis completed")
	print("Analysis completed")



root = Tk()

# This is the section of code which creates the main window
root.geometry('580x700')
root.configure(background='#FFEBCD')
root.title('Harmonic Compatibility (HC)')


# This is the section of code which creates a button
music_b = Button(root, text='Music Folder', bg='#FFEBCD', font=('verdana', 12, 'normal'), command=music_button).place(x=23, y=10)


# This is the section of code which creates a button
analyze_b = tk.Button(root, text='Analyze', bg='#FFEBCD', font=('verdana', 12, 'normal'), command=analyze_button).place(x=453, y=10)

#This is the section of code which creates a TreeView
e = ttk.Treeview(root, column=("c1", "c2", "c3", "c4"), show='headings', selectmode="browse", height = 30)
e.bind('<Double-1>', main_song_selected)
e.heading("c1", text="Song Name")
e.heading("c2", text="HC(%)")
e.heading("c3", text="T(st)")
e.heading("c4", text="THC(%)")
e.column('c1', stretch=tk.YES, minwidth=50, width=450)
e.column('c2', stretch=tk.YES, minwidth=40, width=45)
e.column('c3', stretch=tk.YES, minwidth=40, width=40)
e.column('c4', stretch=tk.YES, minwidth=40, width=45)
e.place(x=0, y=80)

# This is the section of code which creates the a label
text1 = Label(fg="black", font=("verdana", 9), bg='#FFEBCD')
text1.place(x=23,y=45)
text2 = Label(fg="black", font=("verdana", 9), bg='#FFEBCD')
text2.place(x=23,y=60)

text3 = Label(text= "holu :)", fg="black", font=("Helvetica", 10), bg='#FFEBCD')
text3.place(x=185,y=15)
text4 = Label(fg="black", font=("Helvetica", 10), bg='#FFEBCD')
text4.place(x=185,y=30)

root.mainloop()
