import os
import sys
import json
import traceback
import contextlib

from mindbender import api, schema

from .vendor.Qt import QtWidgets, QtCore
from . import lib, pages

self = sys.modules[__name__]
self._window = None

LabelRole = QtCore.Qt.UserRole + 1
PathRole = QtCore.Qt.UserRole + 2
ObjectRole = QtCore.Qt.UserRole + 3


class Window(QtWidgets.QDialog):

    def __init__(self, config, parent=None):
        super(Window, self).__init__(parent)
        self.setWindowTitle("Mindbender Launcher")

        # NOTE(marcus): This will eventually be per-project,
        # and updated during traversal to a particular project.
        browser = pages.Browser(config)
        monitor = pages.Monitor()

        # Composition
        #
        #
        #
        #
        #
        body = QtWidgets.QTabWidget()
        body.addTab(browser, "Browser")
        body.addTab(monitor, "Monitor")

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(body)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(0)

        names = {
            body: "ApplicationBody",
            browser: "BrowserPage",
            monitor: "TerminalPage",
        }

        for widget, name in names.items():
            widget.setObjectName(name)

        self.data = {
            "state": {
                "currentRoot": None
            },
            "pages": {
                "browser": browser,
                "monitor": monitor
            },
        }

        browser.launched.connect(self.on_launched)
        browser.refreshed.connect(self.on_refreshed)
        # monitor.killed.connect(self.on_killed)
        # monitor.brought_to_front.connect(self.on_brought_to_front)
        # monitor.maximised.connect(self.on_maximised)

        self.resize(800, 450)

        # Defaults
        monitor.hide()

    def on_refreshed(self):
        self.refresh()

    def on_launched(self, data):
        environment = os.environ.copy()
        environment.update(data["environment"])
        self.launch(data["app"], environment)

    def refresh(self, root=None):
        self.setWindowTitle(root)

        if root is not None:
            self.data["state"]["currentRoot"] = root

        browser = self.data["pages"]["browser"]
        browser.refresh(self.data["state"]["currentRoot"])

    def launch(self, app, environment):

        env = dict()

        for key, value in environment.items():
            env[key] = value.format(**os.environ)

        try:
            popen = lib.launch(
                executable=app["executable"],
                args=app.get("args", []),
                environment=env
            )
        except ValueError:
            return traceback.print_exc()

        except OSError:
            return traceback.print_exc()

        monitor = self.data["pages"]["monitor"]
        monitor.monitor_process({
            "instance": popen,
            "app": app,
        })


def show(debug=False):
    """Display Launcher GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False

    """

    if self._window:
        self._window.close()
        del(self._window)

    root = os.getcwd()

    # Load config
    try:
        with open(".config") as f:
            config = json.load(f)
    except IOError:
        config = dict()

    schema.validate(config, "config")

    stylepath = os.path.join(os.path.dirname(__file__), "app.css")
    with open(stylepath) as f:
        style = f.read()

    with lib.application():
        window = Window(config)
        window.setStyleSheet(style)
        window.show()
        window.refresh(root)

        self._window = window
