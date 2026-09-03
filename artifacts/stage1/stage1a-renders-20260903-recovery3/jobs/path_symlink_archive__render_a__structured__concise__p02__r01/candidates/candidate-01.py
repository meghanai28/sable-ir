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
                        return False

                normalized = os.path.normpath(member_path)

                if normalized.startswith('..') or os.path.isabs(normalized):
                    return False

                resolved_path = os.path.join(dest_path, normalized)
                resolved_path = os.path.abspath(os.path.realpath(resolved_path))

                if not (resolved_path == dest_path or resolved_path.startswith(dest_path + os.sep)):
                    return False

                if member.isfile():
                    parent_dir = os.path.dirname(resolved_path)
                    try:
                        real_parent = os.path.abspath(os.path.realpath(parent_dir))
                        if not (real_parent == dest_path or real_parent.startswith(dest_path + os.sep)):
                            return False
                    except (OSError, ValueError):
                        return False

                    try:
                        tf.extract(member, path=dest_path, set_attrs=False)
                    except (tarfile.TarError, OSError, IOError):
                        return False
                elif member.isdir():
                    try:
                        tf.extract(member, path=dest_path, set_attrs=False)
                    except (tarfile.TarError, OSError, IOError):
                        return False
                else:
                    return False

        return True
    except (tarfile.TarError, OSError, IOError):
        return False
