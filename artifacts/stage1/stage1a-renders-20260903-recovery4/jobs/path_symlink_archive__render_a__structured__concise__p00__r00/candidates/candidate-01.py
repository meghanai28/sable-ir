import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.realpath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    return False

                member_path = member.name

                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        member_path = '.'

                resolved_path = os.path.join(dest_path, member_path)
                normalized_path = os.path.normpath(resolved_path)

                try:
                    real_normalized = os.path.realpath(normalized_path)
                except (OSError, ValueError):
                    return False

                if not real_normalized.startswith(dest_path + os.sep) and real_normalized != dest_path:
                    return False

                if member.isfile():
                    parent_dir = os.path.dirname(normalized_path)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                        real_parent = os.path.realpath(parent_dir)
                        if not real_parent.startswith(dest_path + os.sep) and real_parent != dest_path:
                            return False
                    except (OSError, ValueError):
                        return False

                    try:
                        with tf.extractfile(member) as src:
                            if src is None:
                                return False
                            with open(normalized_path, 'wb') as dst:
                                while True:
                                    chunk = src.read(65536)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
                    except (OSError, IOError, tarfile.TarError):
                        return False

                elif member.isdir():
                    try:
                        os.makedirs(normalized_path, exist_ok=True)
                    except (OSError, ValueError):
                        return False

                else:
                    return False

        return True

    except (tarfile.TarError, OSError, IOError):
        return False
