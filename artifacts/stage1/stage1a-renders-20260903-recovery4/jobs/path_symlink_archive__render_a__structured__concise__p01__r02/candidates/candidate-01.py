import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_real = os.path.realpath(dest_path)
        if not os.path.isdir(dest_real):
            try:
                os.makedirs(dest_real, exist_ok=True)
            except OSError:
                return False

        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf:
                if member.issym() or member.islnk():
                    return False

                member_name = member.name
                if member_name.startswith('/'):
                    member_name = member_name[1:]
                elif member_name.startswith(('//', '../')):
                    pass

                joined = os.path.join(dest_real, member_name)
                normalized = os.path.normpath(joined)
                resolved = os.path.realpath(normalized)

                if not resolved.startswith(dest_real + os.sep) and resolved != dest_real:
                    return False

                if member.isfile():
                    parent_dir = os.path.dirname(resolved)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError:
                        return False

                    if not parent_dir.startswith(dest_real + os.sep) and parent_dir != dest_real:
                        return False

                    try:
                        with tf.extractfile(member) as fobj:
                            if fobj is None:
                                return False
                            with open(resolved, 'wb') as out:
                                while True:
                                    chunk = fobj.read(65536)
                                    if not chunk:
                                        break
                                    out.write(chunk)
                    except (OSError, IOError, tarfile.TarError):
                        return False

                elif member.isdir():
                    try:
                        os.makedirs(resolved, exist_ok=True)
                    except OSError:
                        return False

                else:
                    return False

        return True

    except (OSError, IOError, tarfile.TarError):
        return False
