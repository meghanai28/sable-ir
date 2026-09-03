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
                            parent_dir = resolved_path
                            try:
                                parent_resolved = os.path.realpath(os.path.abspath(parent_dir))
                            except (OSError, ValueError):
                                return False
                            if parent_resolved != base_path and not parent_resolved.startswith(base_path + os.sep):
                                return False
                        elif member.isdir():
                            pass
                    elif resolved_path.startswith(base_path + os.sep):
                        parent_dir = os.path.dirname(resolved_path)
                        while parent_dir and parent_dir != base_path:
                            try:
                                parent_resolved = os.path.realpath(os.path.abspath(parent_dir))
                            except (OSError, ValueError):
                                return False
                            if parent_resolved != base_path and not parent_resolved.startswith(base_path + os.sep):
                                return False
                            parent_dir = os.path.dirname(parent_dir)
                            if parent_dir == os.path.dirname(parent_dir):
                                break
                        try:
                            final_parent = os.path.realpath(os.path.abspath(os.path.dirname(resolved_path)))
                        except (OSError, ValueError):
                            return False
                        if final_parent != base_path and not final_parent.startswith(base_path + os.sep):
                            return False
                    else:
                        return False

                    if member.isdir():
                        try:
                            os.makedirs(resolved_path, exist_ok=True)
                        except OSError:
                            return False
                    elif member.isfile():
                        try:
                            os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
                        except OSError:
                            return False
                        try:
                            with tf.extractfile(member) as fobj:
                                if fobj is None:
                                    return False
                                data = fobj.read()
                            with open(resolved_path, 'wb') as outf:
                                outf.write(data)
                        except (OSError, ValueError, TypeError):
                            return False
                else:
                    return False

        return True
    except (OSError, tarfile.TarError, ValueError):
        return False
