import os
import sys
import string

from PyQt5 import QtCore

self = sys.modules[__name__]
self._path = os.path.dirname(__file__)
self._current_task = None


class FormatDict(dict):
    def __missing__(self, key):
        return "{" + key + "}"


def core_resource(*path):
    import avalon
    res_root = os.path.dirname(os.path.dirname(avalon.__file__))
    path = os.path.join(res_root, "res", *path)
    return path.replace("\\", "/")


def resource(*path):
    path = os.path.join(self._path, "res", *path)
    return path.replace("\\", "/")


def schedule(task, delay=10):
    """Delay execution of `task` by `delay` milliseconds

    As opposed to a plain `QTimer.singleShot`, this will also
    ensure that only one task is ever queued at any one time.

    """

    try:
        self._current_task.stop()
    except AttributeError:
        # No task currently running
        pass

    timer = QtCore.QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(task)
    timer.start(delay)

    self._current_task = timer


def stream(stream):
    for line in iter(stream.readline, ""):
        yield line


def get_apps(project):
    """Define dynamic Application classes for project using `.toml` files

    Args:
        project (dict): project document from the database

    Returns:
        list: list of dictionaries
    """

    import avalon.lib
    import avalon.api as api

    apps = []
    for app in project["config"]["apps"]:
        try:
            app_definition = avalon.lib.get_application(app['name'])
        except Exception as exc:
            print("Unable to load application: %s - %s" % (app['name'], exc))
            continue

        # Get from app definition, if not there from app in project
        icon = app_definition.get("icon", app.get("icon", "folder-o"))
        color = app_definition.get("color", app.get("color", None))
        order = app_definition.get("order", app.get("order", 0))
        label = app.get("label", app_definition.get("label", app["name"]))

        action = type(
            "app_%s" % app["name"],
            (api.Application,),
            {
                "name": app['name'],
                "label": label,
                "icon": icon,
                "color": color,
                "order": order,
                "config": app_definition.copy()
            }
        )

        apps.append(action)

    return apps


def partial_format(s, mapping):

    formatter = string.Formatter()
    mapping = FormatDict(**mapping)

    return formatter.vformat(s, (), mapping)
