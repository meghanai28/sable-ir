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

                joined_path = os.path.join(dest_path, member_path)
                try:
                    resolved_path = os.path.abspath(os.path.realpath(joined_path))
                except (OSError, ValueError):
                    return False

                if resolved_path != dest_path:
                    try:
                        common_prefix = os.path.commonpath([resolved_path, dest_path])
                    except ValueError:
                        return False
                    if common_prefix != dest_path:
                        return False

                if member.isfile():
                    parent_dir = os.path.dirname(resolved_path)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except (OSError, ValueError):
                        return False

                    try:
                        file_obj = tf.extractfile(member)
                        if file_obj is None:
                            return False
                        with open(resolved_path, 'wb') as f:
                            while True:
                                chunk = file_obj.read(65536)
                                if not chunk:
                                    break
                                f.write(chunk)
                    except (OSError, IOError, ValueError):
                        return False

                elif member.isdir():
                    try:
                        os.makedirs(resolved_path, exist_ok=True)
                    except (OSError, ValueError):
                        return False

                else:
                    return False

        return True

    except (tarfile.TarError, OSError, ValueError):
        return False
