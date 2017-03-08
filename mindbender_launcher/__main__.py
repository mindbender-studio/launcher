import sys
import imp
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug")

    args = parser.parse_args()

    if args.debug:
        pass

    missing = list()
    for dependency in ("mindbender",
                       "pyblish",
                       "pyblish_maya",
                       "pyblish_maya",
                       "pyblish_nuke",
                       "pyblish_lite",
                       "pyblish_qml",
                       ):
        if not imp.find_module(dependency):
            missing.append(dependency)

    assert not missing, (
        "Missing dependenc(ies): '%s'" % "', '".join(missing)
    )

    from .app import show
    show()


sys.exit(main())
