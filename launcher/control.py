import os
import sys
import copy
import traceback
import contextlib

from PyQt5 import QtCore

from avalon import api, io
from avalon.vendor import six
from . import lib, model, terminal

PY2 = sys.version_info[0] == 2


@contextlib.contextmanager
def stdout():
    old = sys.stdout

    stdout = six.StringIO()
    sys.stdout = stdout

    try:
        yield stdout
    finally:
        sys.stdout = old


Signal = QtCore.pyqtSignal
Slot = QtCore.pyqtSlot
Property = QtCore.pyqtProperty

DEFAULTS = {
    "icon": {
        "project": "map",
        "silo": "database",
        "asset": "plus-square",
        "task": "male",
        "app": "file",
    }
}

# Logging levels
DEBUG = 1 << 0
INFO = 1 << 1
WARNING = 1 << 2
ERROR = 1 << 3
CRITICAL = 1 << 4


class Controller(QtCore.QObject):
    # An item was clicked, causing an environment change
    #
    # Arguments:
    #   label (str): The visual name of the item
    #
    pushed = Signal(str, arguments=["label"])

    # The back button was pressed
    popped = Signal()

    # The hierarchy was navigated, either forwards or backwards
    navigated = Signal()

    def __init__(self, root, parent=None):
        super(Controller, self).__init__(parent)

        self._root = root
        self._breadcrumbs = list()
        self._processes = list()
        self._model = model.Model(
            items=[],
            roles=[
                "_id",
                "name",
                "label",
                "icon",
                "group"
            ])

        self._actions = model.Model(
            items=[],
            roles=[
                "_id",
                "name",
                "label",
                "icon",
                "color"
            ])

        # Store the registered actions for a projects
        self._registered_actions = list()

        # A "frame" contains the environment at a given point
        # in the asset hierarchy. For example, browsing all the
        # way to an application yields a fully qualified frame
        # usable when launching an application.
        # The current frame is visualised by the Terminal in the GUI.
        self._frames = list()

    @Property(str, constant=True)
    def title(self):
        return (api.Session["AVALON_LABEL"] or "Avalon") + " Launcher"

    @Slot()
    def launch_explorer(self):
        """Initial draft of this method is subject to change and might
        migrate to another module"""
        # Todo: find a cleaner way, with .toml file for example

        print("Opening Explorer")

        # Get the current environment
        frame = self.current_frame()
        frame["environment"]["root"] = self._root

        # When we are outside of any project, do nothing
        config = frame.get("config", None)
        if config is None:
            print("No project found in configuration")
            return

        template = config['template']['work']
        path = lib.partial_format(template, frame["environment"])

        # Keep only the part of the path that was formatted
        path = os.path.normpath(path.split("{", 1)[0])

        print(path)
        if os.path.exists(path):
            import subprocess
            # todo(roy): Make this cross OS compatible (currently windows only)
            subprocess.Popen(r'explorer "{}"'.format(path))

    def current_frame(self):
        """Shorthand for the current frame"""
        try:
            # Nested dictionaries require deep copying.
            return copy.deepcopy(self._frames[-1])

        except IndexError:
            return dict()

    @Property("QVariant", notify=navigated)
    def breadcrumbs(self):
        return self._breadcrumbs

    @Property("QVariant", notify=navigated)
    def environment(self):
        try:
            frame = self._frames[-1]["environment"]
        except (IndexError, KeyError):
            return list()
        else:
            return [
                {"key": key, "value": str(value)}
                for key, value in frame.items()
            ]

    @Property(model.Model, notify=navigated)
    def actions(self):
        return self._actions

    @Property(model.Model, notify=navigated)
    def model(self):
        return self._model

    @Slot(str)
    def command(self, command):
        if not command:
            return

        output = command + "\n"

        with stdout() as out:
            try:
                exec(command, globals())
            except Exception:
                output += traceback.format_exc()
            else:
                output += out.getvalue()

        if output:
            terminal.log(output.rstrip())

    @Slot(QtCore.QModelIndex)
    def push(self, index):
        name = model.data(index, "name")
        self.breadcrumbs.append(name)

        level = len(self.breadcrumbs)
        handler = {
            1: self.on_project_changed,
            2: self.on_silo_changed,
            3: self.on_asset_changed,
            4: self.on_task_changed
        }[level]

        handler(index)

        # Push the compatible applications
        actions = self.collect_compatible_actions(self._registered_actions)
        self._actions.push(actions)

        self.navigated.emit()

    @Slot(int)
    def pop(self, index=None):

        if index is None:
            # Regular pop behavior
            steps = 1
        elif index < 0:
            # Refresh; go beyond first index
            steps = len(self.breadcrumbs) + 1
        else:
            # Go to index
            steps = len(self.breadcrumbs) - index - 1

        for i in range(steps):
            self._frames.pop()
            self._model.pop()
            self._actions.pop()

            if not self.breadcrumbs:
                self.popped.emit()
                self.navigated.emit()
                return self.init()

            try:
                self.breadcrumbs.pop()
            except IndexError:
                pass
            else:
                self.popped.emit()
                self.navigated.emit()

    def init(self):
        terminal.log("initialising..")
        header = "Root"

        self._model.push([
            dict({
                "_id": project["_id"],
                "icon": DEFAULTS["icon"]["project"],
                "name": project["name"],
            }, **project["data"])
            for project in sorted(io.projects(), key=lambda x: x['name'])
            if project["data"].get("visible", True)  # Discard hidden projects
        ])

        frame = {"environment": {}}
        self._frames[:] = [frame]

        # Discover all registered actions
        discovered_actions = api.discover(api.Action)
        self._registered_actions[:] = discovered_actions

        # Validate actions based on compatibility
        actions = self.collect_compatible_actions(discovered_actions)
        self._actions.push(actions)

        self.pushed.emit(header)
        self.navigated.emit()
        terminal.log("ready")

    def on_project_changed(self, index):
        name = model.data(index, "name")
        api.Session["AVALON_PROJECT"] = name

        # Establish a connection to the project database
        self.log("Connecting to %s" % name, level=INFO)

        frame = self.current_frame()
        project = io.find_one({"type": "project"})

        assert project is not None, "This is a bug"

        frame["config"] = project["config"]

        # Get available project actions and the application actions
        actions = api.discover(api.Action)
        apps = lib.get_apps(project)
        self._registered_actions[:] = actions + apps

        silos = io.distinct("silo")
        self._model.push([
            dict({
                "name": silo,
                "icon": DEFAULTS["icon"]["silo"],
            })
            for silo in sorted(silos)
        ])

        frame["project"] = project["_id"]
        frame["environment"]["project"] = name
        frame["environment"].update({
            "project_%s" % key: str(value)
            for key, value in project["data"].items()
        })

        self._frames.append(frame)
        self.pushed.emit(name)

    def on_silo_changed(self, index):
        name = model.data(index, "name")
        api.Session["AVALON_SILO"] = name

        frame = self.current_frame()

        self._model.push([
            dict({
                "_id": doc["_id"],
                "name": doc["name"],
                "icon": DEFAULTS["icon"]["asset"],
            }, **doc["data"])
            for doc in sorted(
                io.find({
                    "type": "asset",
                    "parent": frame["project"],
                    "silo": name
                }),

                # Hard-sort by group
                # TODO(marcus): Sorting should really happen in
                # the model, via e.g. a Proxy.
                key=lambda item: (
                    # Sort by group
                    item["data"].get(
                        "group",

                        # Put items without a
                        # group at the top
                        "0"),

                    # Sort inner items by name
                    item["name"]
                )
            )

            # Discard hidden items
            if doc["data"].get("visible", True)
        ])

        frame["environment"]["silo"] = name

        self._frames.append(frame)
        self.pushed.emit(name)

    def on_asset_changed(self, index):
        name = model.data(index, "name")
        api.Session["AVALON_ASSET"] = name

        frame = self.current_frame()

        frame["asset"] = model.data(index, "_id")
        frame["environment"]["asset"] = name

        # TODO(marcus): These are going to be accessible
        # from database, not from the environment.
        asset = io.find_one({"_id": frame["asset"]})
        api.Session["AVALON_HIERARCHY"] = asset["data"]["hierarchy"]

        frame["environment"].update({
            "asset_%s" % key: value
            for key, value in asset["data"].items()
        })

        # Get tasks from the project's configuration
        project_tasks = [task for task in frame["config"].get("tasks", [])]

        # Get the tasks assigned to the asset
        asset_tasks = asset.get("data", {}).get("tasks", None)
        if asset_tasks is not None:
            # If the task is in the project configuration than get the settings
            # from the project config to also support its icons, etc.
            task_config = {task['name']: task for task in project_tasks}
            tasks = [task_config.get(name, {"name": name})
                     for name in asset_tasks]
        else:
            # if no `asset.data['tasks']` override then
            # get the tasks from project configuration
            tasks = project_tasks

        # If task has no icon use fallback icon
        for task in tasks:
            if "icon" not in task:
                task['icon'] = DEFAULTS['icon']['task']

        self._model.push(sorted(tasks, key=lambda t: t["name"]))

        self._frames.append(frame)
        self.pushed.emit(name)

    def on_task_changed(self, index):
        name = model.data(index, "name")
        api.Session["AVALON_TASK"] = name

        frame = self.current_frame()
        self._model.push([])

        frame["environment"]["task"] = name

        self._frames.append(frame)
        self.pushed.emit(name)

    @Slot(QtCore.QModelIndex)
    def trigger_action(self, index):

        name = model.data(index, "name")

        # Get the action
        Action = next((a for a in self._registered_actions if a.name == name),
                      None)
        assert Action, "No action found"
        action = Action()

        # Run the action within current session
        self.log("Running action: %s" % name, level=INFO)
        popen = action.process(api.Session.copy())
        # Action might return popen that pipes stdout
        # in which case we listen for it.
        process = {}
        if popen and hasattr(popen, "stdout") and popen.stdout is not None:

            class Thread(QtCore.QThread):
                messaged = Signal(str)

                def run(self):
                    for line in lib.stream(process["popen"].stdout):
                        self.messaged.emit(line.rstrip())
                    self.messaged.emit("%s killed." % process["name"])

            thread = Thread()
            thread.messaged.connect(
                lambda line: terminal.log(line, terminal.INFO)
            )

            process.update({
                "name": name,
                "action": action,
                "thread": thread,
                "popen": popen
            })

            self._processes.append(process)

            thread.start()

        return process

    def log(self, message, level=DEBUG):
        print(message)

    def collect_compatible_actions(self, actions):
        """Collect all actions which are compatible with the environment

        Each compatible action will be translated to a dictionary to ensure
        the action can be visualized in the launcher.

        Args:
            actions (list): list of classes

        Returns:
            list: collection of dictionaries sorted on order int he
        """

        compatible = []
        for Action in actions:
            frame = self.current_frame()

            # Build a session from current frame
            session = {"AVALON_{}".format(key.upper()): value for
                       key, value in frame.get("environment", {}).items()}
            session["AVALON_PROJECTS"] = api.registered_root()
            if not Action().is_compatible(session):
                continue

            compatible.append({
                "name": str(Action.name),
                "icon": str(Action.icon or "cube"),
                "label": str(Action.label or Action.name),
                "color": getattr(Action, "color", None),
                "order": Action.order
            })

        # Sort by order and name
        compatible = sorted(compatible, key=lambda action: (action["order"],
                                                            action["name"]))

        return compatible


def dirs(root):
    try:
        base, dirs, files = next(os.walk(root))
    except (IOError, StopIteration):
        # Ignore non-existing dirs
        return list()

    return dirs
