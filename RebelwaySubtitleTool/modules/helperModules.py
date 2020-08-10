from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtWidgets import QTreeWidgetItem, QFileDialog, QTreeView, QPushButton, QStyledItemDelegate, QStyleOptionProgressBar, QApplication, QStyle
from hashlib import md5
import os, pprint, enum, pathlib, binascii, zlib, struct


##################################################################################################
##################################################################################################
###
### Classes, Enums, and override functions. Also helpers for PyQt
###
##################################################################################################
##################################################################################################


## DataType = This is for creating set data on items, and this way, instead of setting 0, 1, 2 etc... we can instead use a enum.
class DT(enum.IntEnum):
    FilePath = 0
    FileName = 1
    FileType = 2
    ETagChecksum = 3
    FileSize = 4
    OSType = 5
    JobName = 6
    Bucket = 7
    CompletionTime = 8
    CreationTime = 9
    LanguageCode = 10

## Determines if the OS type is a file or folder. Just a helper class.
class OS_Type(enum.IntEnum):
    File = 0
    Folder = 1

## Providing a LIMITED filetype supportion, as I don't want to really want to provide support for everything
class FileType(enum.Enum):
    mp4 = "video/mp4"
    mkv = "video/x-matroska"
    srt = "sub/subrip-subtitle"
    ass = "sub/substation-alpha"
    vtt = "sub/web-video-text-track"
    unknown = "extra/unknown"


## New Filedialog! This overwrites the class QFileDialog, and enables the user to select both folders and files in the one dialog.
class FileDialog(QFileDialog):
    def __init__(self, *args):
        QFileDialog.__init__(self, *args)
        self.setOption(self.DontUseNativeDialog, True)
        self.setFileMode(self.ExistingFiles)
        btns = self.findChildren(QPushButton)
        self.openBtn = [x for x in btns if 'open' in str(x.text()).lower()][0]
        self.openBtn.clicked.disconnect()
        self.openBtn.clicked.connect(self.openClicked)
        self.tree = self.findChild(QTreeView)

    def openClicked(self):
        inds = self.tree.selectionModel().selectedIndexes()
        ind = self.tree.selectionModel().currentIndex()
        print(ind)
        files = []
        for i in inds:
            if i.column() == 0:
                files.append(os.path.join(str(self.directory().absolutePath()), str(i.data())))
        self.selectedFiles = files
        self.hide()
        self.close()

    def accept (self):
        inds = self.tree.selectionModel().selectedIndexes()
        ind = self.tree.selectionModel().currentIndex()
        print(ind)
        files = []
        for i in inds:
            if i.column() == 0:
                files.append(os.path.join(str(self.directory().absolutePath()), str(i.data())))
        self.selectedFiles = files
        self.hide()
        self.close()

    def filesSelected(self):
        return self.selectedFiles

## Returns a file extension, limited only to mp4, mkv, srt, ass and vtt.
def GetFileType(file):
    fileSuffix = pathlib.Path(file).suffix.lower()
    if fileSuffix == ".mp4":
        fileExt = FileType.mp4
    elif fileSuffix == ".mkv":
        fileExt = FileType.mkv
    elif fileSuffix == ".srt":
        fileExt = FileType.srt
    elif fileSuffix == ".ass":
        fileExt = FileType.ass
    elif fileSuffix == ".vtt":
        fileExt = FileType.vtt
    else:
        fileExt = FileType.unknown
    return fileExt

def checkFile(file):
    fileSuffix = pathlib.Path(file).suffix.lower()
    myFileTypes = [".mp4", ".mkv"]
    
    for myFileType in myFileTypes:
        if fileSuffix == myFileType:
            print(f"True {file}")
            return True

    return False



## Returns all the files that are checked off inside a given QTreeWidget
def LoadFilesCheckStatus(localTree, inType):
	items = get_all_items(localTree)
	for item in items:
		item.setCheckState(0, inType)


def SetItemData(item, **mainArgs):
    if "FILENAME" in mainArgs:
        item.setData(DT.FileName, Qt.UserRole, mainArgs.get("FILENAME"))
    if "FILETYPE" in mainArgs:
        item.setData(DT.FileType, Qt.UserRole, mainArgs.get("FILETYPE"))
    if "FILEPATH" in mainArgs:
        item.setData(DT.FilePath, Qt.UserRole, mainArgs.get("FILEPATH"))
    if "FILESIZE" in mainArgs:
        item.setData(DT.FileSize, Qt.UserRole, mainArgs.get("FILESIZE"))
    if "OSFILETYPE" in mainArgs:
        item.setData(DT.OSType, Qt.UserRole, mainArgs.get("OSFILETYPE"))

    if "CHECKSUM" in mainArgs:
        item.setData(DT.ETagChecksum, Qt.UserRole, mainArgs.get("CHECKSUM"))

    if "JOBNAME" in mainArgs:
        item.setData(DT.JobName, Qt.UserRole, mainArgs.get("JOBNAME"))
    if "BUCKET" in mainArgs:
        item.setData(DT.Bucket, Qt.UserRole, mainArgs.get("BUCKET"))

    if "LANGUAGE" in mainArgs:
        item.setData(DT.LanguageCode, Qt.UserRole, mainArgs.get("LANGUAGE"))
    if "CREATIONTIME" in mainArgs:
        item.setData(DT.CreationTime, Qt.UserRole, mainArgs.get("CREATIONTIME"))
    if "COMPLETEDTIME" in mainArgs:
        item.setData(DT.CompletionTime, Qt.UserRole, mainArgs.get("COMPLETEDTIME"))

    return item

def GetItemData(item, ItemType):
    if isinstance(ItemType, DT):
        return item.data(ItemType, Qt.UserRole)


def InfoWriter(**mainArgs):
    mainText = ""
    if "FILEPATH" in mainArgs:
        mainText = "{0}File path:\n{1}\n\n".format(mainText, mainArgs.get("FILEPATH"))
    if "CHECKSUM" in mainArgs:
        mainText = "{0}File Checksum:\n{1}\n\n".format(mainText, mainArgs.get("CHECKSUM"))
    if "FILESIZE" in mainArgs:
        mainText = "{0}File Size: {1}\n\n".format(mainText, mainArgs.get("FILESIZE"))
    if "FILETYPE" in mainArgs:
        mainText = "{0}File Extension: {1}\n\n".format(mainText, mainArgs.get("FILETYPE"))
    if "JOBNAME" in mainArgs:
        mainText = "{0}Job Name:\n{1}\n\n".format(mainText, mainArgs.get("JOBNAME"))
    if "LANGUAGE" in mainArgs:
        mainText = "{0}Language Code: {1}\n\n".format(mainText, mainArgs.get("LANGUAGE"))
    if "CREATIONTIME" in mainArgs:
        mainText = "{0}Creation Time: {1}\n\n".format(mainText, mainArgs.get("CREATIONTIME"))
    if "COMPLETEDTIME" in mainArgs:
        mainText = "{0}Completed Time: {1}\n\n".format(mainText, mainArgs.get("COMPLETEDTIME"))

    return mainText





## Sets anything into a disabled or enabled status.
def SetItemsDisabled(items, status):
    for item in items:
        item.setDisabled(status)

def SetTreeItems(treeWidget, status):
    items = get_all_items(treeWidget)
    SetItemsDisabled(items, status)
        
        #flags = item.flags()
        #flags.setFlag(Qt.ItemIsEnabled, status)
        #item.setFlags(flags)




##################################################################################################
##################################################################################################
###
### Secondary functions for helping aid the AWS functions.
###
##################################################################################################
################################################################################################## 


## Calculates the correct ETag for a given file. This can be heavy, so recommended it is used in a seperate thread.
def calculate_s3_etag(file_path, chunk_size=8 * 1024 * 1024):
    md5s = []

    with open(file_path, 'rb') as fp:
        while True:
            data = fp.read(chunk_size)
            if not data:
                break
            md5s.append(md5(data))

    if len(md5s) < 1:
        return f'{md5().hexdigest()}'

    if len(md5s) == 1:
        return f'{md5s[0].hexdigest()}'

    digests = b''.join(m.digest() for m in md5s)
    digests_md5 = md5(digests)
    return f'{digests_md5.hexdigest()}-{len(md5s)}'


## Unfinished - Create a transcription job name!
def calculate_job_name(name, tag):
	if len(tag) > 0:
		genMD5 = md5(tag.encode()).hexdigest()
		crc = zlib.crc32(genMD5.encode("utf-8")) & 0xffffffff
		hexCrc = hex(crc).replace("0x", "").upper()
		name = os.path.basename(name).replace(" ", "").replace("-", "_")
		return f"t_{hexCrc}_{name}"


##################################################################################################
##################################################################################################
###
### Functions for the GUI functions.
###
##################################################################################################
##################################################################################################


## Enables a log output function. If the user wishes to see a print function, as well as the GUI, they can.
def LogOutput(settings, message):
    if settings.logEnabled == True:
        pprint.pprint(f"Log: {message}")




## Finds all currently checked items in a QTreeWidget, and returns the given items.
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

## Finds all items in a QTreeWidget, and returns them.
def get_all_items(tree_widget):
    all_items = []
    for i in range(tree_widget.topLevelItemCount()):
        top_item = tree_widget.topLevelItem(i)
        all_items.extend(get_subtree_nodes(top_item))
    return all_items

## Finds all child items of a QTreeWidgetItem, and returns them.
def get_subtree_nodes(tree_widget_item):
    nodes = []
    nodes.append(tree_widget_item)
    for i in range(tree_widget_item.childCount()):
        nodes.extend(get_subtree_nodes(tree_widget_item.child(i)))
    return nodes

## Source - https://www.thepythoncode.com/article/get-directory-size-in-bytes-using-python
## Finds the current directory size of a folder.
def get_directory_size(directory):
    """Returns the `directory` size in bytes."""
    total = 0
    try:
        # print("[+] Getting the size of", directory)
        for entry in os.scandir(directory):
            if entry.is_file():
                # if it's a file, use stat() function
                total += entry.stat().st_size
            elif entry.is_dir():
                # if it's a directory, recursively call this function
                total += get_directory_size(entry.path)
    except NotADirectoryError:
        # if `directory` isn't a directory, get the file size then
        return os.path.getsize(directory)
    except PermissionError:
        # if for whatever reason we can't open the folder, return 0
        return 0
    return total
