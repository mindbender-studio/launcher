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
                "type",
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

        frame = self.current_frame()

        # When we are outside of any project, do nothing
        config = frame.get("config", None)
        if config is None:
            print("No project found in configuration")

        # Get the current environment
        if 'environment' in frame:
            frame["environment"]["root"] = self._root
            if frame.get('type') in ['asset', 'task']:
                hierarchy = frame['data'].get('hierarchy', None)
                if hierarchy is not None:
                    frame['environment']['hierarchy'] = hierarchy
            if frame.get('type') == 'task':
                frame['environment']['task'] = frame['name']
            template = config['template']['work']
            path = lib.partial_format(template, frame["environment"])
        else:
            path = self._root

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

        frame = self.current_frame()

        # If nothing is set as current frame we are at selecting projects
        handler = self.on_project_changed
        if frame:
            handler = {
                "project": self.on_asset_changed,
                "silo": self.on_asset_changed,
                "asset": self.on_asset_changed
            }[frame["type"]]
            if "tasks" in frame and name in frame["tasks"]:
                handler = self.on_task_changed

        handler(index)

        self.breadcrumbs.append(self.current_frame()["name"])

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
            try:
                self._frames.pop()
                self._model.pop()
                self._actions.pop()
            except IndexError:
                pass

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
                "type": project["type"],
                "name": project["name"],
            }, **project["data"])
            for project in sorted(io.projects(), key=lambda x: x['name'])
            if project["data"].get("visible", True)  # Discard hidden projects
        ])

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

        project = io.find_one({"type": "project"})

        assert project is not None, "This is a bug"

        # Get available project actions and the application actions
        actions = api.discover(api.Action)
        apps = lib.get_apps(project)
        self._registered_actions[:] = actions + apps

        db_assets = io.find({"type": "asset"})
        # Backwadrs compatbility with silo
        silos = db_assets.distinct("silo")
        if silos and None in silos:
            silos = None

        if not silos:
            assets = list()
            for asset in db_assets.sort("name", 1):
                # _not_set_ is for cases when visualParent is not used
                vis_p = asset.get("data", {}).get("visualParent", "_not_set_")
                if vis_p is None:
                    assets.append(asset)
                elif vis_p == "_not_set_":
                    assets.append(asset)

            self._model.push([dict({
                "_id": asset["_id"],
                "name": asset["name"],
                "type": asset["type"],
                "icon": DEFAULTS["icon"]["asset"]
            }) for asset in assets])

        else:
            self._model.push([dict({
                "name": silo, "icon": DEFAULTS["icon"]["silo"], "type": "silo"
            }) for silo in sorted(silos)])

        frame = project
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

        self.docs = sorted(
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
        valid_docs = []
        for doc in self.docs:
            # Discard hidden items
            if not doc["data"].get("visible", True):
                continue

            data = {
                "_id": doc["_id"],
                "name": doc["name"],
                "icon": DEFAULTS["icon"]["asset"]
            }
            data.update(doc["data"])

            if "visualParent" in doc["data"]:
                vis_par = doc["data"]["visualParent"]
                if vis_par is not None:
                    continue

            if "label" not in data:
                data["label"] = doc["name"]
            valid_docs.append(data)

        frame["environment"]["silo"] = name
        frame["name"] = name
        frame["type"] = "silo"

        self._frames.append(frame)
        self._model.push(valid_docs)
        self.pushed.emit(name)

    def on_asset_changed(self, index):
        # Backwards compatible way
        _type = model.data(index, "type")
        if _type == "silo":
            return self.on_silo_changed(index)

        name = model.data(index, "name")
        entity = io.find_one({
            "type": "asset",
            "name": name
        })
        api.Session["AVALON_ASSET"] = name

        frame = self.current_frame()

        frame["asset"] = model.data(index, "_id")
        frame["environment"]["asset"] = name

        if entity.get("silo") is None:
            api.Session["AVALON_SILO"] = name
            frame["environment"]["silo"] = name
            frame["asset"] = entity["_id"]

        if 'visualParent' in entity['data']:
            docs = io.find({
                    "type": "asset",
                    "data.visualParent": entity["_id"]
                })
        else:
            docs = io.find({
                "type": "asset",
                "silo": api.Session["AVALON_SILO"]
            })
        self.docs = sorted(
            docs,
            key=lambda item: (
                # Sort by group - Put items without a group at the top
                item["data"].get("group", "0"),
                # Sort inner items by name
                item["name"]
            )
        )
        # TODO(marcus): These are going to be accessible
        # from database, not from the environment.
        asset = io.find_one({"_id": frame["asset"]})
        if "parents" in asset["data"]:
            api.Session["AVALON_HIERARCHY"] = "/".join(
                asset["data"]["parents"]
            )
        frame.update(asset)
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
            tasks = [task_config.get(task_name, {"name": task_name})
                     for task_name in asset_tasks]
        else:
            # if no `asset.data['tasks']` override then
            # get the tasks from project configuration
            tasks = project_tasks

        # If task has no icon use fallback icon
        for task in tasks:
            if "icon" not in task:
                task['icon'] = DEFAULTS['icon']['task']

        sorted_tasks = []
        for task in sorted(tasks, key=lambda t: t["name"]):
            task["group"] = "Tasks"
            sorted_tasks.append(task)

        frame["tasks"] = [task["name"] for task in sorted_tasks]

        valid_docs = []
        for doc in self.docs:
            if "visualParent" not in doc["data"]:
                continue

            if entity.get("silo") is None and doc["data"]["visualParent"] is None:
                valid_docs.append(
                    dict(
                        {
                            "_id": doc["_id"],
                            "name": doc["name"],
                            "type": doc["type"],
                            "icon": DEFAULTS["icon"]["asset"]
                        },
                        **doc["data"]
                    )
                )
            elif doc["data"]["visualParent"] == asset["_id"]:
                valid_docs.append(
                    dict(
                        {
                            "_id": doc["_id"],
                            "name": doc["name"],
                            "type": doc["type"],
                            "icon": DEFAULTS["icon"]["asset"]
                        },
                        **doc["data"]
                    )
                )

        self._model.push(valid_docs + sorted_tasks)

        self._frames.append(frame)
        self.pushed.emit(name)

    def on_task_changed(self, index):
        name = model.data(index, "name")
        api.Session["AVALON_TASK"] = name

        frame = self.current_frame()
        frame["environment"]["task"] = name
        frame["name"] = name
        frame["type"] = "task"

        self._frames.append(frame)
        self._model.push([])
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
