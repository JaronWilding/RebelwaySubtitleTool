from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QTreeWidgetItem


def get_selected_items(incomingTreeWidget):
	checked_items = []
	def recurse(parent_item):
		for i in range(parent_item.childCount()):
			child = parent_item.child(i)
			grand_children = child.childCount()
			if grand_children > 0:
				recurse(child)
			if child.checkState(0) == Qt.Checked:
				checked_items.append(child)

	recurse(incomingTreeWidget.invisibleRootItem())
	return checked_items