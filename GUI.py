import sys
from os import walk
from main import analyze_song, compare_songs
from PyQt5 import uic
from PyQt5.QtWidgets import QMainWindow, QFileDialog, QApplication, QTableWidgetItem

class programGUI(QMainWindow):

    def __init__(self):
        super().__init__()
        uic.loadUi("GUI.ui", self)
        self.analyze_button.setEnabled(False)
        self.music_button.clicked.connect(self.path_click)
        self.analyze_button.clicked.connect(self.analyze_click)
        self.label_print1.setText("Holu :)")
        self.tableWidget.setColumnWidth(0, 416)
        self.tableWidget.setColumnWidth(1, 60)
        self.tableWidget.setColumnWidth(2, 30)
        self.tableWidget.setColumnWidth(3, 60)

        # Global variables initialization
        self._path = []  # <---container
        self.current_song = ''
        self.song_name_list = []
        self.harmonic_compatibility_list = []
        self.pitch_shift_list = []
        self.min_small_scale_comp_list = []
        self._path.append('')

    def path_click(self):

        folderpath = QFileDialog.getExistingDirectory(self, 'Select Folder')
        self._path[0] = (folderpath)
        if self._path[0]!= []:
            self.analyze_button.setEnabled(True)
        self.label_path_1.setText(folderpath[0:82])
        self.label_path_2.setText(folderpath[82:])
        print(folderpath)
        for (dirpath, dirnames, filenames) in walk(folderpath):
            number_songs = len(filenames)
        self.tableWidget.setRowCount(number_songs)

        folder_name = self._path[0]
        self.label_print1.setText('')
        self.label_print2.setText('')
        # Compute harmonic compatibility
        row=0
        for (dirpath, dirnames, filenames) in walk(folder_name):
            for file in filenames:
                self.tableWidget.setItem(row, 0, QTableWidgetItem(file.replace(".mp3", "")))
                self.tableWidget.setItem(row, 1, QTableWidgetItem(''))
                self.tableWidget.setItem(row, 2, QTableWidgetItem(''))
                self.tableWidget.setItem(row, 3, QTableWidgetItem(''))
                row=row+1
            break
        self.show()
        self.tableWidget.activateWindow()
        self.tableWidget.doubleClicked.connect(self.main_song_selected)
        print(self._path[0])

    def main_song_selected(self, index):
        print(index.row())
        folder_name = self._path[0]
        row=0
        for (dirpath, dirnames, filenames) in walk(folder_name):
            for file in filenames:
                if row == index.row():
                    self.current_song = file.replace(".mp3", "")
                row=row+1
            break

        self.label_print1.setText('Now playing: ')
        self.label_print2.setText(self.current_song)
        self.tableWidget.clearContents()

        # Write song path
        current_song_path = folder_name + '/' + self.current_song + ".mp3"
        row=0
        # Compute harmonic compatibility
        for (dirpath, dirnames, filenames) in walk(folder_name):
            for file in filenames:
                candidate_song_path = dirpath + '/' + file
                harmonic_compatibility, pitch_shift, min_small_scale_comp = compare_songs(current_song_path,
                                                                                          candidate_song_path)

                self.tableWidget.setItem(row, 0, QTableWidgetItem(file.replace(".mp3", "")))
                self.tableWidget.setItem(row, 1, QTableWidgetItem(str(round(harmonic_compatibility, 2))))
                self.tableWidget.setItem(row, 2, QTableWidgetItem(str(pitch_shift)))
                self.tableWidget.setItem(row, 3, QTableWidgetItem(str(round(min_small_scale_comp, 2))))
                row=row+1
            break
        self.show()

    def analyze_click(self):
        self.label_print2.setText("Analyzing...")
        folder_name = self._path[0]
        i = 0
        for (dirpath, dirnames, filenames) in walk(folder_name):
            for file in filenames:
                song_path = dirpath + '/' + file
                analyze_song(song_path)
                i = i + 1
                self.label_print1.setText(str(round(i * 100 / len(filenames), 1)) + '% progress completed')
                print(round(i * 100 / len(filenames), 1), '% progress completed')
            break
        self.label_print2.setText("Analysis completed")
        print("Analysis completed")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    GUI = programGUI()
    GUI.show()
    sys.exit(app.exec_())
