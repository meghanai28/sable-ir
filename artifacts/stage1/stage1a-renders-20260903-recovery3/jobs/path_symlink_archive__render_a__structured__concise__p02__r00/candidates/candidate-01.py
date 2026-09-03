import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.realpath(dest_path))
    except (OSError, ValueError):
        return False

    if not os.path.isdir(dest_path):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            for member in members:
                if member.issym() or member.islnk():
                    return False

                if not (member.isfile() or member.isdir()):
                    return False

                member_name = member.name
                if os.path.isabs(member_name):
                    return False

                normalized = os.path.normpath(member_name)
                if normalized.startswith('..') or '..' in normalized.split(os.sep):
                    return False

                full_path = os.path.join(dest_path, normalized)
                try:
                    full_path = os.path.abspath(os.path.realpath(full_path))
                except (OSError, ValueError):
                    return False

                if not full_path.startswith(dest_path + os.sep) and full_path != dest_path:
                    return False

                if member.isdir():
                    try:
                        os.makedirs(full_path, exist_ok=True)
                    except OSError:
                        return False
                elif member.isfile():
                    parent_dir = os.path.dirname(full_path)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError:
                        return False

                    try:
                        with tf.extractfile(member) as src:
                            if src is None:
                                return False
                            with open(full_path, 'wb') as dst:
                                while True:
                                    chunk = src.read(65536)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
                    except (OSError, IOError, tarfile.TarError):
                        return False

        return True
    except (OSError, IOError, tarfile.TarError):
        return False
