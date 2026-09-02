import os


def read_file_from_dir(filename: str, dir_path: str) -> str:
    absolute = os.path.abspath(os.path.join(dir_path, filename))
    if os.path.commonpath((absolute, os.path.abspath(dir_path))) != os.path.abspath(dir_path):
        return ""
    try:
        with open(absolute, encoding="utf-8") as source:
            return source.read()
    except OSError:
        return ""
