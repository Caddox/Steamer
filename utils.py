from pathlib import Path

def human_readable(bytes):
    '''
    Function used for translating a large byte value into something people can
    actually read.
    '''
    for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']:
        if bytes < 1024.0 or unit == 'PiB':
            break
        bytes /= 1024.0

    return f"{bytes:.2f} {unit}"

def check_file_path_existance(path):
    temp = Path(path)
    if temp.exists():
        return True

    return False