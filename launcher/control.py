import os
import sys
import json
import copy
import errno
import shutil
import getpass
import traceback
import contextlib

from PyQt5 import QtCore

from avalon import api, io, schema
from avalon.vendor import toml, six
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

        # A "frame" contains the environment at a given point
        # in the asset hierarchy. For example, browsing all the
        # way to an application yields a fully qualified frame
        # usable when launching an application.
        # The current frame is visualised by the Terminal in the GUI.
        self._frames = list()

    @Property(str, constant=True)
    def title(self):
        return (api.Session["AVALON_LABEL"] or "Avalon") + " Launcher"

    def launch(self, name):
        """Launch `app`

        Arguments:
            name (str): Name of app

        """

        application_definition = lib.which_app(name)

        if application_definition is None:
            return terminal.log("Application Definition for '%s' not found."
                                % name, terminal.ERROR)

        try:
            with open(application_definition) as f:
                app = toml.load(f)
                terminal.log(json.dumps(app, indent=4), terminal.DEBUG)
                schema.validate(app, "application")
        except (schema.ValidationError,
                schema.SchemaError,
                toml.TomlDecodeError) as e:
            terminal.log("Application definition was invalid.", terminal.ERROR)
            terminal.log("%s" % e, terminal.ERROR)
            return terminal.log(
                " - %s" % application_definition, terminal.ERROR)

        executable = lib.which(app["executable"])

        if executable is None:
            return terminal.log(
                "'%s' not found on your PATH\n%s"
                % (app["executable"], os.getenv("PATH")), terminal.ERROR
            )

        frame = self.current_frame()
        frame["environment"]["root"] = self._root
        frame["environment"]["app"] = app["application_dir"]

        template_private = frame["config"]["template"]["work"]

        try:
            workdir = template_private.format(**dict(
                user=getpass.getuser(),
                **frame["environment"]
            ))

        except KeyError as e:
            return terminal.log(
                "Missing environment variable: %s" % e, terminal.ERROR)

        # TODO(marcus): These shouldn't be necessary
        # once the templates are used.
        # ----------------------------------------------------------------------
        template_rootpath = template_private.split("{silo}")[0]
        template_assetpath = template_private.split("{asset}")[0] + "{asset}"
        template_taskpath = template_private.split("{task}")[0] + "{task}"

        silospath = template_rootpath.format(**frame["environment"])
        assetpath = template_assetpath.format(**frame["environment"])
        taskpath = template_taskpath.format(**frame["environment"])

        frame["environment"]["silospath"] = silospath
        frame["environment"]["assetpath"] = assetpath
        frame["environment"]["taskpath"] = taskpath
        frame["environment"]["workdir"] = workdir
        # ----------------------------------------------------------------------

        # TODO(marcus): These will eventually replace the name-based
        # references currently stored in the environment.
        frame["environment"]["_project"] = frame["project"]
        frame["environment"]["_asset"] = frame["asset"]

        environment = os.environ.copy()

        environment = dict(environment, **{
            "AVALON_" + key.upper(): str(value)
            for key, value in frame["environment"].items()
        })

        try:
            app = lib.dict_format(app, **environment)
        except KeyError as e:
            terminal.log(
                "Application error: variable %s "
                "not found in application .json" % e, terminal.ERROR)
            terminal.log(
                json.dumps(environment, indent=4, sort_keys=True),
                terminal.ERROR)
            return terminal.log(
                "This is typically a bug in the pipeline, "
                "ask your developer.", terminal.ERROR)

        for key, value in app.get("environment", {}).items():
            if isinstance(value, list):
                # Treat list values as application_definition variables
                environment[key] = os.pathsep.join(value)

            elif isinstance(value, six.string_types):
                if PY2:
                    # Protect against unicode in the environment
                    encoding = sys.getfilesystemencoding()
                    environment[key] = value.encode(encoding)
                else:
                    environment[key] = value

            else:
                terminal.log(
                    "'%s': Unsupported environment variable in %s"
                    % (value, application_definition), terminal.ERROR)
                raise TypeError("Unsupported environment variable")

        try:
            os.makedirs(workdir)
            terminal.log(
                "Creating working directory '%s'"
                % workdir, terminal.INFO)

        except OSError as e:

            # An already existing working directory is fine.
            if e.errno == errno.EEXIST:
                terminal.log(
                    "Existing working directory found.",
                    terminal.INFO)

            else:
                terminal.log(
                    "Could not create working directory.",
                    terminal.ERROR)
                return terminal.log(
                    traceback.format_exc(),
                    terminal.ERROR)

        else:
            terminal.log("Creating default directories..", terminal.DEBUG)
            for dirname in app.get("default_dirs", []):
                terminal.log(" - %s" % dirname, terminal.DEBUG)
                os.makedirs(os.path.join(workdir, dirname))

        # Perform application copy
        for src, dst in app.get("copy", {}).items():
            dst = os.path.join(workdir, dst)

            try:
                terminal.log("Copying %s -> %s" % (src, dst))
                shutil.copy(src, dst)
            except OSError as e:
                terminal.log(
                    "Could not copy application file: %s" % e, terminal.ERROR)
                terminal.log(
                    " - %s -> %s" % (src, dst), terminal.ERROR)

        item = next(
            app for app in frame["config"]["apps"]
            if app["name"] == name
        )
        args = item.get("args", []) + app.get("arguments", [])

        try:
            popen = lib.launch(
                executable=executable,
                args=args,
                environment=environment,
                cwd=workdir
            )
        except ValueError:
            return terminal.log(traceback.format_exc())

        except OSError:
            return terminal.log(traceback.format_exc())

        except Exception as e:
            terminal.log("Something unexpected happened..")
            return terminal.log(traceback.format_exc())

        else:
            terminal.log(
                json.dumps(environment, indent=4, sort_keys=True),
                terminal.DEBUG)
            terminal.log("Launching {executable} {args}".format(
                executable=executable,
                args=" ".join(args))
            )

        process = {}

        class Thread(QtCore.QThread):
            messaged = Signal(str)

            def run(self):
                for line in lib.stream(process["popen"].stdout):
                    self.messaged.emit(line.rstrip())
                self.messaged.emit("%s killed." % process["app"]["executable"])

        # lib.launch might not pipe stdout,
        # in which case we can't listen for it.
        if popen.stdout is not None:
            thread = Thread()
            thread.messaged.connect(
                lambda line: terminal.log(line, terminal.INFO)
            )

            process.update({
                "app": app,
                "thread": thread,
                "popen": popen
            })

            self._processes.append(process)

            thread.start()

        return process

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
                {"key": key, "value": value}
                for key, value in frame.items()
            ]

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
            4: self.on_task_changed,
            5: self.on_app_changed,
        }[level]

        handler(index)
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
            for project in io.projects()

            # Discard hidden projects
            if project["data"].get("visible", True)
        ])

        frame = {
            "environment": {},
        }
        self._frames[:] = [frame]

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

        silos = io.distinct("silo")
        self._model.push([
            dict({
                "name": silo,
                "icon": DEFAULTS["icon"]["silo"],
            })
            for silo in silos
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
        frame["environment"].update({
            "asset_%s" % key: value
            for key, value in asset["data"].items()
        })

        self._model.push([
            dict({
                "icon": DEFAULTS["icon"]["task"]
            }, **task)
            for task in sorted(
                frame["config"].get("tasks", []),
                key=lambda t: t["name"])
        ])

        self._frames.append(frame)
        self.pushed.emit(name)

    def on_task_changed(self, index):
        name = model.data(index, "name")
        api.Session["AVALON_TASK"] = name

        frame = self.current_frame()

        applications_data = []
        sorted_apps = sorted(
            frame["config"].get("apps", []), key=lambda a: a["name"]
        )
        for app in sorted_apps:
            data = {"icon": DEFAULTS["icon"]["app"]}

            # Default label from application toml
            application_definition = lib.which_app(app["name"])
            with open(application_definition) as f:
                data["label"] = toml.load(f)["label"]

            # Overrides in config
            data.update(app)

            applications_data.append(data)

        self._model.push(applications_data)

        frame["environment"]["task"] = name

        self._frames.append(frame)
        self.pushed.emit(name)

    def on_app_changed(self, index):
        """Launch application on clicking it"""
        name = model.data(index, "name")
        api.Session["AVALON_APP"] = name

        self.launch(name)
        self.breadcrumbs.pop()

    def log(self, message, level=DEBUG):
        print(message)


def dirs(root):
    try:
        base, dirs, files = next(os.walk(root))
    except (IOError, StopIteration):
        # Ignore non-existing dirs
        return list()

    return dirs
