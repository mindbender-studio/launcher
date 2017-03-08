import os
import sys
import time
import threading

from mindbender import api
from ..vendor.Qt import QtWidgets, QtCore
from .. import lib

self = sys.modules[__name__]
self._window = None

LabelRole = QtCore.Qt.UserRole + 1
PathRole = QtCore.Qt.UserRole + 2
ObjectRole = QtCore.Qt.UserRole + 3
ProcessKilledRole = QtCore.Qt.UserRole + 4


class Widget(QtWidgets.QWidget):

    killed = QtCore.Signal()
    maximised = QtCore.Signal()
    brought_to_front = QtCore.Signal()

    # Threaded signals
    _process_killed = QtCore.Signal(dict)
    _process_launched = QtCore.Signal(dict)
    _process_wrote = QtCore.Signal(QtWidgets.QWidget, str)

    def __init__(self, parent=None):
        super(Widget, self).__init__(parent)

        body = QtWidgets.QWidget()

        processes = QtWidgets.QListWidget()
        processes.setFixedWidth(150)
        process_placeholder = QtWidgets.QLabel("No process.")

        # Actions
        #
        #
        #
        #
        actions = QtWidgets.QWidget()
        actions.setFixedWidth(200)

        btn_front = QtWidgets.QPushButton("Bring to front")
        btn_maximise = QtWidgets.QPushButton("Maximise")
        btn_kill = QtWidgets.QPushButton("Kill")
        spacer = QtWidgets.QWidget()

        layout = QtWidgets.QVBoxLayout(actions)
        layout.addWidget(btn_front)
        layout.addWidget(btn_maximise)
        layout.addWidget(btn_kill)
        layout.addWidget(spacer, 1)  # Push buttons to top

        layout = QtWidgets.QHBoxLayout(body)
        layout.addWidget(processes)
        layout.addWidget(process_placeholder)
        layout.addWidget(actions)
        layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(body)
        layout.setContentsMargins(0, 0, 0, 0)

        names = {
            body: "TerminalBody",
            processes: "TerminalProcesses",
        }

        for widget, name in names.items():
            widget.setObjectName(name)

        self.data = {
            "views": {
                "processes": processes,
            },

            # Reference to each running subprocess
            "runningApps": {
                "0": {
                    "widget": process_placeholder,
                }
            }
        }

        processes.currentItemChanged.connect(self.on_process_changed)

        # Forward events to parent
        btn_front.clicked.connect(self.brought_to_front.emit)
        btn_kill.clicked.connect(self.on_killed)
        btn_maximise.clicked.connect(self.maximised.emit)

        # Threaded communication
        self._process_launched.connect(self.on_process_launched)
        self._process_wrote.connect(self.on_process_wrote)
        self._process_killed.connect(self.on_process_killed)

        self.update_processes()

    def on_killed(self):
        view = self.data["views"]["processes"]
        process = view.currentItem().data(ObjectRole)

        print("Terminating %s" % process)
        process["instance"].kill()

    def on_process_killed(self, process):
        print("%s killed" % process)
        process["item"].setProperty("killed", True)

    def on_process_launched(self, process):
        # Wait 2 seconds before enabling user to launch another app.
        button = self.data["buttons"]["launch"]
        button.setEnabled(False)
        QtCore.QTimer.singleShot(2000, lambda: button.setEnabled(True))

        self.monitor_process(process)

    def on_process_wrote(self, widget, line):
        print("on_process_wrote..")
        widget.append(line.rstrip())

    def monitor_process(self, process):
        """Keep an eye on output from launched application"""
        def _monitor(widget):
            print("Monitoring %s.." % process["instance"])
            for line in lib.stream(process["instance"].stdout):
                self._process_wrote.emit(widget, line)
            self._process_killed.emit(process)

        widget = QtWidgets.QTextEdit()
        widget.setLineWrapMode(widget.NoWrap)
        widget.setReadOnly(True)
        widget.append("Running '%s'.." % process["app"]["executable"])
        widget.setStyleSheet("""
            QTextEdit {
                background: black;
                color: white;
            }
        """)

        body = self.findChild(QtWidgets.QWidget, "TerminalBody")
        body.layout().insertWidget(1, widget)

        thread = threading.Thread(target=_monitor, args=[widget])
        thread.daemon = True
        thread.start()

        time = api.time()
        process.update({
            "thread": thread,
            "widget": widget,
            "time": time
        })

        for app in self.data["runningApps"].values():
            app["widget"].hide()

        self.data["runningApps"][time] = process
        self.update_processes()

        return thread

    def on_process_changed(self, current, previous):
        if not current:
            return

        if not current.data(QtCore.Qt.ItemIsEnabled):
            return

        for app in self.data["runningApps"].values():
            app["widget"].hide()

        process = current.data(ObjectRole)
        process["widget"].show()

    def update_processes(self):
        print("update_processes..")
        view = self.data["views"]["processes"]
        view.clear()

        for process in self.data["runningApps"].values():

            # Placeholder process have no app
            if "app" not in process:
                continue

            label = os.path.basename(process["app"]["executable"])

            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemIsEnabled, True)
            item.setData(ObjectRole, process)
            view.addItem(item)

            process["item"] = item
