import os

import mindbender
from ..vendor.Qt import QtWidgets, QtCore
from .. import lib

LabelRole = QtCore.Qt.UserRole + 1
PathRole = QtCore.Qt.UserRole + 2
ObjectRole = QtCore.Qt.UserRole + 3


class Widget(lib.StyledQWidget):

    launched = QtCore.Signal(dict)
    refreshed = QtCore.Signal()

    def __init__(self, config, parent=None):
        super(Widget, self).__init__(parent)

        self.config = config

        #  ___________________________________
        # |        |        |        |        |
        # |        |        |        |        |
        # |        |        |        |        |
        # |        |        |        |        |
        # |        |        |        |        |
        # |________|________|________|________|
        #
        projects = QtWidgets.QListWidget()
        assets = QtWidgets.QListWidget()
        tasks = QtWidgets.QListWidget()
        apps = QtWidgets.QListWidget()

        #  _______ ________
        # |       \        \
        # | assets |  shots |
        # |________|________|
        #
        silos = QtWidgets.QTabBar()
        silos.addTab("Assets")
        silos.addTab("Film")

        assets_container = lib.StyledQWidget()
        layout = QtWidgets.QVBoxLayout(assets_container)
        layout.addWidget(silos)
        layout.addWidget(assets)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Actions
        #
        #
        #
        #
        actions = lib.StyledQWidget()
        actions.setFixedWidth(200)

        btn_launch = QtWidgets.QPushButton("Launch")
        btn_refresh = QtWidgets.QPushButton("Refresh")
        spacer = lib.StyledQWidget()

        layout = QtWidgets.QVBoxLayout(actions)
        layout.addWidget(btn_launch)
        layout.addWidget(btn_refresh)
        layout.addWidget(spacer, 1)  # Push buttons to top

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(projects)
        layout.addWidget(assets_container)
        layout.addWidget(tasks)
        layout.addWidget(apps)
        layout.addWidget(actions)
        layout.setContentsMargins(0, 0, 0, 0)

        names = {
            self: "BrowserBody",
        }

        for widget, name in names.items():
            widget.setObjectName(name)

        self.data = {
            "views": {
                "projects": projects,
                "assets": assets,
                "tasks": tasks,
                "apps": apps,
            },

            "buttons": {
                "launch": btn_launch,
                "refresh": btn_refresh,
            },

            "silos": silos,

            "state": {
                # Root since last refresh
                "root": None,
            }
        }

        silos.currentChanged.connect(self.on_silo_changed)

        projects.currentItemChanged.connect(self.on_project_changed)
        assets.currentItemChanged.connect(self.on_asset_changed)
        tasks.currentItemChanged.connect(self.on_task_changed)
        apps.currentItemChanged.connect(self.on_app_changed)

        btn_launch.clicked.connect(self.on_launch_clicked)
        btn_refresh.clicked.connect(self.on_refresh_clicked)

        btn_launch.setEnabled(False)

    def on_launch_clicked(self):
        button = self.data["buttons"]["launch"]
        button.setEnabled(False)

        self.launched.emit(self._as_dict())

        QtCore.QTimer.singleShot(2000, lambda: button.setEnabled(True))

    def on_refresh_clicked(self):
        print("Whaat")
        button = self.data["buttons"]["refresh"]
        button.setEnabled(False)

        self.refreshed.emit()

        QtCore.QTimer.singleShot(1000, lambda: button.setEnabled(True))

    def _as_dict(self):
        views = self.data["views"]
        silos = self.data["silos"]

        # Names
        project_name = views["projects"].currentItem().data(LabelRole)
        asset_name = views["assets"].currentItem().data(LabelRole)
        task_name = views["tasks"].currentItem().data(LabelRole)
        silo_name = silos.tabText(silos.currentIndex())

        # Paths
        project_path = views["projects"].currentItem().data(PathRole)
        asset_path = views["assets"].currentItem().data(PathRole)

        app = views["apps"].currentItem().data(ObjectRole)

        return {
            "environment": {
                "MINDBENDER_PROJECTNAME": project_name,
                "MINDBENDER_ASSETNAME": asset_name,
                "MINDBENDER_TASKNAME": task_name,
                "MINDBENDER_SILONAME": silo_name,

                "MINDBENDER_PROJECTPATH": project_path,
                "MINDBENDER_ASSETPATH": asset_path,
                "PYTHONPATH": os.environ["PYTHONPATH"] + ";C:/pythonpath/mindbender/maya/pythonpath"
            },

            "app": app
        }

    def on_project_changed(self, current, previous):
        """User changed project"""
        self.data["buttons"]["launch"].setEnabled(False)
        self.data["views"]["assets"].clear()

        if not current:
            return

        if not current.data(QtCore.Qt.ItemIsEnabled):
            return

        root = current.data(PathRole)
        lib.schedule(lambda: self.update_assets(project=root))

    def on_silo_changed(self, index):
        """User changed silo"""
        projects = self.data["views"]["projects"]

        tasks = self.data["views"]["assets"]
        tasks.clear()

        root = projects.currentItem().data(PathRole)
        lib.schedule(lambda: self.update_assets(project=root))

    def on_asset_changed(self, current, previous):
        """User changed asset"""
        self.data["buttons"]["launch"].setEnabled(False)
        self.data["views"]["tasks"].clear()

        if not current:
            return

        if not current.data(QtCore.Qt.ItemIsEnabled):
            return

        root = current.data(PathRole)
        lib.schedule(lambda: self.update_tasks(asset=root))

    def on_task_changed(self, current, previous):
        """User changed task"""
        self.data["buttons"]["launch"].setEnabled(False)
        self.data["views"]["apps"].clear()

        if not current:
            return

        # if not current.data(QtCore.Qt.ItemIsEnabled):
        #     return

        root = current.data(PathRole)
        self.update_apps(root)

    def on_app_changed(self, current, previous):
        if not current:
            return

        if not current.data(QtCore.Qt.ItemIsEnabled):
            return

        self.data["buttons"]["launch"].setEnabled(True)

    def refresh(self, root):
        for view in self.data["views"].values():
            view.clear()

        self.data["state"]["root"] = root
        self.data["buttons"]["launch"].setEnabled(False)

        view = self.data["views"]["projects"]
        for path in lib.walk(root):
            label = os.path.basename(path)
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemIsEnabled, True)
            item.setData(PathRole, path)
            item.setData(LabelRole, label)
            view.addItem(item)

        view.setCurrentItem(view.item(0))

    def update_assets(self, project):
        views = self.data["views"]
        silos = self.data["silos"]
        silo = silos.tabText(silos.currentIndex())
        root = os.path.join(project, silo)

        no_items = True
        for path in lib.walk(root):
            label = os.path.basename(path)
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemIsEnabled, True)
            item.setData(PathRole, path)
            item.setData(LabelRole, label)
            views["assets"].addItem(item)
            no_items = False

        if no_items:
            item = QtWidgets.QListWidgetItem("No assets")
            item.setData(QtCore.Qt.ItemIsEnabled, False)
            views["assets"].addItem(item)

    def update_tasks(self, asset):
        root = os.path.join(asset, "work")

        tasks = {
            task["name"]: task
            for task in self.config.get("tasks", [])
        }

        existing = {
            os.path.basename(path): path
            for path in lib.walk(root)
        }

        no_items = True
        for name, task in tasks.items():
            label = task.get("label", task["name"])
            path = existing.get(name)

            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemIsEnabled, name in existing)
            item.setData(LabelRole, label)
            item.setData(PathRole, path)
            self.data["views"]["tasks"].addItem(item)
            no_items = False

        if no_items:
            item = QtWidgets.QListWidgetItem("No items")
            item.setData(QtCore.Qt.ItemIsEnabled, False)
            self.data["views"]["tasks"].addItem(item)

    def update_apps(self, task):
        view = self.data["views"]["apps"]

        no_items = True
        for app in self.config.get("apps", {}):
            label = app.get("label", app["executable"])
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.ItemIsEnabled, True)
            item.setData(ObjectRole, app)
            item.setData(LabelRole, label)
            view.addItem(item)
            no_items = False

        if no_items:
            item = QtWidgets.QListWidgetItem("No apps")
            item.setData(QtCore.Qt.ItemIsEnabled, False)
            self.data["views"]["apps"].addItem(item)
