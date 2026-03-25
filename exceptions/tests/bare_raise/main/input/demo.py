def bad():
    raise  # flagged: bare raise outside except


def nested_bad():
    if True:
        raise  # flagged: still outside except


def good_reraise():
    try:
        pass
    except Exception:
        raise  # ok: re-raises inside except


def good_nested_except():
    try:
        pass
    except TypeError:
        try:
            pass
        except ValueError:
            raise  # ok: inside nested except


def good_raise_with_arg():
    raise ValueError("something")  # ok: not bare
