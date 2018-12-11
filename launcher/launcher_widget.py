"""Application entry-point"""

# Standard library
import os
import sys

# Dependencies
from avalon import io
from PyQt5 import QtCore, QtGui, QtQml, QtWidgets, QtQuick

# Local libraries
from . import control, terminal, lib

QML_IMPORT_DIR = lib.resource("qml")
APP_PATH = lib.resource("qml", "main.qml")
ICON_PATH = lib.resource("icon", "main.png")

# TODO: Re-implement icons of tray menu after resolving #323
# Issue 323: https://github.com/getavalon/core/issues/323


class Launcher(QtWidgets.QWidget):

    def __init__(self, root, source):
        super(Launcher, self).__init__()#sys.argv)

        engine = QtQml.QQmlApplicationEngine()
        engine.objectCreated.connect(self.on_object_created)
        # engine.warnings.connect(self.on_warnings)
        engine.addImportPath(QML_IMPORT_DIR)

        try:
            io.install()
        except IOError:
            raise  # Server refused to connect

        # Install actions
        from . import install
        install()

        terminal.init()

        controller = control.Controller(root, self)
        engine.rootContext().setContextProperty("controller", controller)
        engine.rootContext().setContextProperty("terminal", terminal.model)

        self._tray = None
        self.window = None
        self.engine = engine
        self.controller = controller
        self.window = object
        self.controller.init()
        engine.load(QtCore.QUrl.fromLocalFile(source))

    def on_object_created(self, object, url):
        if object is None:
            print("Could not load QML file..")
            sys.exit(1)
        else:
            self.window = object
            self.controller.init()

    # def on_warnings(self, warnings):
    #     for warning in warnings:
    #         print(warning.toString())
