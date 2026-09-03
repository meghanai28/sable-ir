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
                member_name = member.name

                if member.issym() or member.islnk():
                    return False

                if not member.isfile() and not member.isdir():
                    return False

                target_path = os.path.join(dest_path, member_name)
                try:
                    target_path = os.path.abspath(os.path.realpath(target_path))
                except (OSError, ValueError):
                    return False

                if not target_path.startswith(dest_path + os.sep) and target_path != dest_path:
                    return False

                if member.isdir():
                    try:
                        os.makedirs(target_path, exist_ok=True)
                    except OSError:
                        return False
                elif member.isfile():
                    try:
                        parent_dir = os.path.dirname(target_path)
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError:
                        return False

                    try:
                        file_obj = tf.extractfile(member)
                        if file_obj is None:
                            return False
                        with open(target_path, 'wb') as out_f:
                            while True:
                                chunk = file_obj.read(65536)
                                if not chunk:
                                    break
                                out_f.write(chunk)
                    except (OSError, tarfile.TarError, IOError):
                        return False
                else:
                    return False

        return True
    except (OSError, tarfile.TarError):
        return False
