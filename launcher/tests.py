import os
import sys
import json
import shutil
import tempfile

from nose.tools import (
    assert_equals,
)

from . import control

self = sys.modules[__name__]


def setup():
    self.root = tempfile.mkdtemp()
    self.config = {
        "apps": [
            {
                "name": "python",
                "args": ["-u", "-c", "print('Something nice')"]
            }
        ],
        "tasks": [
            {
                "label": "animation",
                "name": "animation"
            },
            {
                "label": "modeling",
                "name": "modeling"
            },
            {
                "label": "rigging",
                "name": "rigging"
            },
            {
                "label": "lookdev",
                "name": "lookdev"
            }
        ]
    }

    os.environ["PATH"] += os.pathsep.join([
        os.environ["PATH"],
        self.root
    ])

    with open(os.path.join(self.root, "python.json"), "w") as f:
        json.dump({
            "executable": "python",
            "application_dir": "python",
            "label": "Python 2.7"
        }, f)


def teardown():
    shutil.rmtree(self.root)


def test_launch():
    """Launching an app works ok"""

    ctrl = control.Controller(self.root, self.config, None)
    ctrl.push("hulk")
    ctrl.push("assets")
    ctrl.push("Bruce")
    ctrl.push("modeling")
    # ctrl.push("python")
    process = ctrl.launch("python")
    # popen = process["popen"]
    # print(popen)

    # import time
    # time.sleep(1)
    assert False
