from pathlib import Path


def human_readable(bytes):
    """
    Function used for translating a large byte value into something people can
    actually read.
    """
    for unit in ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]:
        if bytes < 1024.0 or unit == "PiB":
            break
        bytes /= 1024.0

    return f"{bytes:.2f} {unit}"


def check_file_path_existence(path):
    """
    Checks if a given path exists.
    Path can be a string or a pathlib.Path object.

    They both get converted to pathlib.Path objects anyways...
    """
    temp = Path(path)
    if temp.exists():
        return True

    return False
