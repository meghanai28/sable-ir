import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_real = os.path.realpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf:
                if member.issym() or member.islnk():
                    return False

                member_name = member.name
                if member_name.startswith('/'):
                    member_name = member_name[1:]
                elif member_name.startswith('./'):
                    member_name = member_name[2:]

                normalized = os.path.normpath(member_name)
                if normalized.startswith('..') or os.path.isabs(normalized):
                    return False

                target_path = os.path.join(dest_real, normalized)
                target_real = os.path.realpath(target_path)

                if not target_real.startswith(dest_real + os.sep) and target_real != dest_real:
                    return False

                if member.isfile():
                    parent_dir = os.path.dirname(target_real)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except (OSError, ValueError):
                        return False

                    try:
                        with tf.extractfile(member) as fobj:
                            if fobj is None:
                                return False
                            data = fobj.read()
                        with open(target_real, 'wb') as out_f:
                            out_f.write(data)
                    except (OSError, IOError, ValueError):
                        return False
                elif member.isdir():
                    try:
                        os.makedirs(target_real, exist_ok=True)
                    except (OSError, ValueError):
                        return False
                else:
                    return False

        return True
    except (OSError, tarfile.TarError, ValueError):
        return False
