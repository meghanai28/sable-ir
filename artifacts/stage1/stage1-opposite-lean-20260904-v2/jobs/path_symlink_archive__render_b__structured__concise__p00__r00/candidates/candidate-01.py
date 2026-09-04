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

                if not (member.isfile() or member.isdir()):
                    return False

                member_path = member.name

                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        member_path = '.'

                target_path = os.path.join(dest_path, member_path)
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
                    except (OSError, tarfile.TarError):
                        return False

                    try:
                        with open(target_path, 'wb') as f:
                            while True:
                                chunk = file_obj.read(65536)
                                if not chunk:
                                    break
                                f.write(chunk)
                    except OSError:
                        return False
                    finally:
                        file_obj.close()

                    try:
                        os.chmod(target_path, member.mode)
                    except OSError:
                        pass

    except (OSError, tarfile.TarError):
        return False

    return True
