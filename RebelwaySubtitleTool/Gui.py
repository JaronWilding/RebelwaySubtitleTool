from PyQt5.QtWidgets import QMainWindow, QApplication, QDesktopWidget, QPushButton, QDialog, QGroupBox, QHBoxLayout,QVBoxLayout 
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QRect
import sys


class Window(QDialog):
	def __init__(self):
		super().__init__()
		
		self.InitWindow("Rebelway AWS Tool", 100, 100, 300, 100)


	def createLayout(self):

		self.groupBox = QGroupBox("What is your name and pass?")
		hboxLayout = QHBoxLayout()

		button = QPushButton("Click Me", self)
		button.clicked.connect(Clickme)
		button.setMinimumHeight(40)

		button1 = QPushButton("Click Me 2", self)
		button1.clicked.connect(Clickme)
		button1.setMinimumHeight(40)

		button2 = QPushButton("Click Me 3", self)
		button2.clicked.connect(Clickme)
		button2.setMinimumHeight(40)

		hboxLayout.addWidget(button)
		hboxLayout.addWidget(button1)
		hboxLayout.addWidget(button2)

		self.groupBox.setLayout(hboxLayout)


		


	def InitWindow(self, title, top, left, width, height):
		self.setWindowIcon(QtGui.QIcon("icons/rw_logo.png"))

		self.setWindowTitle(title)
		self.setGeometry(left, top, width, height)
		self.Center()

		self.createLayout()

		self.vbox = QVBoxLayout()
		self.vbox.addWidget(self.groupBox)
		self.setLayout(self.vbox)
		

		self.show()

	def Center(self):
		qr = self.frameGeometry()
		cp = QDesktopWidget().availableGeometry().center()
		qr.moveCenter(cp)
		self.move(qr.topLeft())



def Clickme():
	print("Hello everyone")

if __name__ == "__main__":
	App = QApplication(sys.argv)
	window = Window()
	sys.exit(App.exec())



