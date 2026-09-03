import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        base_path = os.path.realpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False

    if not os.path.isdir(base_path):
        try:
            os.makedirs(base_path, exist_ok=True)
        except OSError:
            return False

    try:
        base_path = os.path.realpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf:
                if member.issym() or member.islnk():
                    return False

                if member.isfile() or member.isdir():
                    member_name = member.name

                    if os.path.isabs(member_name):
                        return False

                    candidate_path = os.path.join(base_path, member_name)
                    try:
                        resolved_path = os.path.realpath(os.path.abspath(candidate_path))
                    except (OSError, ValueError):
                        return False

                    if resolved_path == base_path:
                        if member.isfile():
                            return False
                    elif not resolved_path.startswith(base_path + os.sep):
                        return False

                    if member.isfile():
                        parent_dir = os.path.dirname(resolved_path)
                        try:
                            resolved_parent = os.path.realpath(os.path.abspath(parent_dir))
                        except (OSError, ValueError):
                            return False

                        if resolved_parent != base_path and not resolved_parent.startswith(base_path + os.sep):
                            return False

                        try:
                            os.makedirs(parent_dir, exist_ok=True)
                        except OSError:
                            return False

                        try:
                            with tf.extractfile(member) as fobj:
                                if fobj is None:
                                    return False
                                with open(resolved_path, 'wb') as out_f:
                                    while True:
                                        chunk = fobj.read(65536)
                                        if not chunk:
                                            break
                                        out_f.write(chunk)
                        except (OSError, IOError, tarfile.TarError):
                            return False

                    elif member.isdir():
                        try:
                            os.makedirs(resolved_path, exist_ok=True)
                        except OSError:
                            return False

                else:
                    return False

            return True

    except (OSError, IOError, tarfile.TarError):
        return False
    except Exception:
        return False
