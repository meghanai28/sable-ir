import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_abs = os.path.normpath(os.path.abspath(dest_path))
    dest_prefix = dest_abs + os.sep

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    return False

                if not member.isfile() and not member.isdir():
                    return False

                member_name = member.name
                candidate_path = os.path.normpath(os.path.join(dest_abs, member_name))

                if not candidate_path.startswith(dest_prefix) and candidate_path != dest_abs:
                    return False

                if member.isdir():
                    try:
                        os.makedirs(candidate_path, exist_ok=True)
                    except OSError:
                        return False
                elif member.isfile():
                    try:
                        parent_dir = os.path.dirname(candidate_path)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)
                        with tf.extractfile(member) as src:
                            if src is None:
                                return False
                            with open(candidate_path, 'wb') as dst:
                                while True:
                                    chunk = src.read(65536)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
                    except (OSError, TypeError):
                        return False
    except (OSError, tarfile.TarError):
        return False

    return True
