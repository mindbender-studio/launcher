"""Application entry-point"""

# Standard library
import os
import sys

# Dependencies
from avalon import io
from PyQt5 import QtCore, QtGui, QtQml, QtWidgets

# Local libraries
from . import control, terminal, lib

QML_IMPORT_DIR = lib.resource("qml")
APP_PATH = lib.resource("qml", "main.qml")
ICON_PATH = lib.core_resource("icons", "png", "avalon-logo-16.png")
SPLASH_PATH = lib.core_resource("icons", "png", "splash.png")

# TODO: Re-implement icons of tray menu after resolving #323
# Issue 323: https://github.com/getavalon/core/issues/323


class Application(QtWidgets.QApplication):

    def __init__(self, root, source):
        super(Application, self).__init__(sys.argv)
        self.setWindowIcon(QtGui.QIcon(ICON_PATH))

        pixmap = QtGui.QPixmap(SPLASH_PATH)
        splash = QtWidgets.QSplashScreen(pixmap)
        splash.show()
        self._splash = splash

        engine = QtQml.QQmlApplicationEngine()
        engine.objectCreated.connect(self.on_object_created)
        engine.warnings.connect(self.on_warnings)
        engine.addImportPath(QML_IMPORT_DIR)

        self._splash.showMessage("Connecting database...",
                                 QtCore.Qt.AlignBottom, QtCore.Qt.black)

        try:
            io.install()
        except IOError:
            raise  # Server refused to connect

        # Install actions
        from . import install
        install()

        self._splash.showMessage("Starting Avalon Launcher...",
                                 QtCore.Qt.AlignBottom, QtCore.Qt.black)

        terminal.init()

        controller = control.Controller(root, self)
        engine.rootContext().setContextProperty("controller", controller)
        engine.rootContext().setContextProperty("terminal", terminal.model)

        self._tray = None
        self.window = None
        self.engine = engine
        self.controller = controller

        engine.load(QtCore.QUrl.fromLocalFile(source))

        self.setQuitOnLastWindowClosed(False)

    def on_object_created(self, object, url):
        if object is None:
            print("Could not load QML file..")
            sys.exit(1)

        else:
            self.window = object
            self.init_tray()
            self._splash.close()

            self.controller.init()
            print("Success")

    def on_warnings(self, warnings):
        for warning in warnings:
            print(warning.toString())

    def init_tray(self):

        tray = QtWidgets.QSystemTrayIcon(self.windowIcon(), parent=self)
        tray.setToolTip("Avalon Launcher")

        # Build the right-mouse context menu for the tray icon
        menu = QtWidgets.QMenu()

        def window_show():
            self.window.show()
            self.window.raise_()
            self.window.requestActivate()

        show = QtWidgets.QAction("Show", self)
        show.triggered.connect(window_show)
        menu.addAction(show)

        def on_quit():
            # fix crash on quit with QML window open
            self.closeAllWindows()

            # fix tray icon remaining visible until hover over
            self._tray.hide()

            self.quit()

        quit = QtWidgets.QAction("Quit", self)
        quit.triggered.connect(on_quit)
        menu.addAction(quit)
        tray.setContextMenu(menu)

        # Add the double clicked behavior
        def on_tray_activated(reason):
            if reason == QtWidgets.QSystemTrayIcon.Context:
                return

            if self.window.isVisible():
                self.window.hide()

            elif reason == QtWidgets.QSystemTrayIcon.Trigger:
                window_show()

        tray.activated.connect(on_tray_activated)

        self._tray = tray

        tray.show()
        tray.showMessage("Avalon", "Launcher tray started.", 500)


def main(root, demo=False):
    """Start the Qt-runtime and show the window"""

    root = os.path.realpath(root)

    print("Starting avalon-launcher")
    app = Application(root, APP_PATH)
    return app.exec_()
