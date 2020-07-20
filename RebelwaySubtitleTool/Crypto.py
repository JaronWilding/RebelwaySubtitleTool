import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QAction, QMenu
from PyQt5.QtGui import QIcon



class GUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        self.setWindowTitle("Hello World")
        self.resize(400, 300)

        self.addMenusAndStatus()

    def addMenusAndStatus(self):
        self.statusBar().showMessage("This Meszsage")

        menubar = self.menuBar()

        # Adds a file section to the menu
        file_menu = menubar.addMenu("File")

        ## Creates the menu + the icon
        new_icon = QIcon("icons/new_icon.png")
        new_action = QAction(new_icon, "New", self)

        # Adds the action + sets the status
        new_action.setStatusTip("New File")
        file_menu.addAction(new_action)

        # Sets seperator
        file_menu.addSeparator()

        # Exit token added to the menu, with status and function
        exit_icon = QIcon("icons/exit_icon.png")
        exit_action = QAction(exit_icon, "Exit", self)
        exit_action.setStatusTip("Click to exit the application")

        exit_action.triggered.connect(self.close)
        exit_action.setShortcut("Ctrl+Q")
     
        # Exit token added to action
        file_menu.addAction(exit_action)

        # Adds an edit to the menu
        edit_menu = menubar.addMenu("Edit")

       




if __name__ == "__main__":
    app = QApplication(sys.argv)
    gui = GUI()
    gui.show()
    sys.exit(app.exec_())
    