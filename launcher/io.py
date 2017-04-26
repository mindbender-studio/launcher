import sys
import firebase

from PyQt5 import QtCore

self = sys.modules[__name__]
self.db = None
self.url = "https://mindbender-assets.firebaseio.com"
self.terminal = None

DEBUG = 1 << 0
INFO = 1 << 1
WARNING = 1 << 2


class Model(QtCore.QAbstractListModel):
    def __init__(self, items=None, parent=None):
        super(Model, self).__init__(parent)
        self._items = items or list()

    def append(self, item):
        self.beginInsertRows(QtCore.QModelIndex(),
                             self.rowCount(),
                             self.rowCount())
        self._items.append(item)
        self.endInsertRows()

    def rowCount(self, parent=None):
        return len(self._items)

    def data(self, index, role=QtCore.QModelIndex()):
        if role == QtCore.Qt.UserRole + 0:
            return self._items[index.row()]

    def roleNames(self):
        return {
            QtCore.Qt.UserRole + 0: b"line",
        }


def init():
    self.db = firebase.FirebaseApplication(self.url)
    self.terminal = Model()


def log(line, level=INFO):
    self.terminal.append(line)
