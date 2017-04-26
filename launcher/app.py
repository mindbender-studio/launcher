"""Application entry-point"""

# Standard library
import os
import sys
import json

# Dependencies
from PyQt5 import QtCore, QtGui, QtQml

# Local libraries
from . import control, io

MODULE_DIR = os.path.dirname(__file__)
QML_IMPORT_DIR = os.path.join(MODULE_DIR, "qml")
APP_PATH = os.path.join(MODULE_DIR, "qml", "main.qml")
ICON_PATH = os.path.join(MODULE_DIR, "icon.png")


class Application(QtGui.QGuiApplication):

    def __init__(self, root, config, source):
        super(Application, self).__init__(sys.argv)
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))

        engine = QtQml.QQmlApplicationEngine()
        engine.objectCreated.connect(self.on_object_created)
        engine.warnings.connect(self.on_warnings)
        engine.addImportPath(QML_IMPORT_DIR)

        io.init()

        controller = control.Controller(root, config, self)
        engine.rootContext().setContextProperty("controller", controller)
        engine.rootContext().setContextProperty("terminal", io.terminal)

        self.engine = engine
        self.controller = controller

        engine.load(QtCore.QUrl.fromLocalFile(source))

    def on_object_created(self, object, url):
        if object is None:
            print("Could not load QML file..")
            sys.exit(1)

        else:
            self.controller.init()
            print("Success")

    def on_warnings(self, warnings):
        for warning in warnings:
            print(warning.toString())


def which(program):
    """Locate `program` in PATH

    Arguments:
        program (str): Name of program, e.g. "python"

    """

    def is_exe(fpath):
        if os.path.isfile(fpath) and os.access(fpath, os.X_OK):
            return True
        return False

    for path in os.environ["PATH"].split(os.pathsep):
        for ext in os.getenv("PATHEXT", "").split(os.pathsep):
            fname = program + ext.lower()
            abspath = os.path.join(path.strip('"'), fname)

            if is_exe(abspath):
                return abspath

    return None


def main(root, demo=False):
    """Start the Qt-runtime and show the window"""

    # Load config
    root = os.path.realpath(root)
    configpath = os.path.join(root, ".config")

    try:
        with open(configpath) as f:
            config = json.load(f)
    except IOError:
        config = dict()

    print("Starting mindbender-launcher")
    # print("Passing config: %s" % config)
    app = Application(root, config, APP_PATH)
    return app.exec_()
