import os
import sys
import subprocess
import contextlib

from .vendor.Qt import QtCore, QtWidgets

self = sys.modules[__name__]
self._current_task = None


def launch(executable, args=None, environment=None):
    """Launch a new subprocess of `args`

    Arguments:
        executable (str): Relative or absolute path to executable
        args (list): Command passed to `subprocess.Popen`
        environment (dict, optional): Custom environment passed
            to Popen instance.

    Returns:
        Popen instance of newly spawned process

    Exceptions:
        OSError on internal error
        ValueError on `executable` not found

    """

    CREATE_NO_WINDOW = 0x08000000
    IS_WIN32 = sys.platform == "win32"

    abspath = executable

    # Convert relative path to absolute
    # if not os.path.isabs(abspath):
    #     abspath = which(abspath)

    # if abspath is None:
    #     raise ValueError("'%s' was not found." % executable)

    kwargs = dict(
        args=[abspath] + args or list(),
        env=environment or os.environ,

        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,

        # Output `str` through stdout on Python 2 and 3
        universal_newlines=True,

        shell=True
    )

    if IS_WIN32:
        kwargs["creationflags"] = CREATE_NO_WINDOW

    popen = subprocess.Popen(**kwargs)

    return popen


def stream(stream):
    for line in iter(stream.readline, ""):
        yield line


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


def schedule(task, delay=100):
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
    timer.start()

    self._current_task = timer


def walk(root):
    try:
        base, dirs, files = next(os.walk(root))
    except IOError:
        # Ignore non-existing dirs
        return

    for dirname in dirs:
        yield os.path.join(root, dirname)


@contextlib.contextmanager
def application():
    app = QtWidgets.QApplication.instance()

    if not app:
        print("Starting new QApplication..")
        app = QtWidgets.QApplication(sys.argv)
        yield app
        app.exec_()
    else:
        print("Using existing QApplication..")
        yield app


class StyledQWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(StyledQWidget, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground)
