import os
import sys

self = sys.modules[__name__]
self._path = os.path.dirname(__file__)

try:
    basestring
except NameError:
    basestring = str


def resource(*path):
    path = os.path.join("..", "res", *path)
    return os.path.normpath(path)


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


def which_app(app):
    """Locate `app` in PATH

    Arguments:
        app (str): Name of app, e.g. "python"

    """

    for path in os.environ["PATH"].split(os.pathsep):
        fname = app + ".json"
        abspath = os.path.join(path.strip('"'), fname)

        if os.path.isfile(abspath):
            return abspath

    return None


def dict_format(original, **kwargs):
    """Recursively format the values in *original* with *kwargs*.

    Example:
        >>> sample = {"key": "{value}", "sub-dict": {"sub-key": "sub-{value}"}}
        >>> dict_format(sample, value="Bob") == \
            {'key': 'Bob', 'sub-dict': {'sub-key': 'sub-Bob'}}
        True

    """

    new_dict = dict()
    new_list = list()

    if isinstance(original, dict):
        for key, value in original.items():
            if isinstance(value, dict):
                new_dict[key.format(**kwargs)] = dict_format(value, **kwargs)
            elif isinstance(value, list):
                new_dict[key.format(**kwargs)] = dict_format(value, **kwargs)
            elif isinstance(value, basestring):
                new_dict[key.format(**kwargs)] = value.format(**kwargs)
            else:
                new_dict[key.format(**kwargs)] = value

        return new_dict

    else:
        assert isinstance(original, list)
        for value in original:
            if isinstance(value, dict):
                new_list.append(dict_format(value, **kwargs))
            elif isinstance(value, list):
                new_list.append(dict_format(value, **kwargs))
            elif isinstance(value, basestring):
                new_list.append(value.format(**kwargs))
            else:
                new_list.append(value)

        return new_list
