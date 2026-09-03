import os
import tarfile


def _is_within_root(root: str, path: str) -> bool:
    root_norm = os.path.normpath(root)
    path_norm = os.path.normpath(path)
    root_nc = os.path.normcase(root_norm)
    path_nc = os.path.normcase(path_norm)
    if root_nc == path_nc:
        return True
    if not root_nc.endswith(os.sep):
        root_nc += os.sep
    return path_nc.startswith(root_nc)


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.realpath(os.path.abspath(dest_path))
        os.makedirs(dest_path, exist_ok=True)
    except Exception:
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    return False

                member_name = member.name.lstrip('/')
                if not member_name:
                    member_name = '.'
                if os.path.isabs(member_name):
                    return False

                target = os.path.normpath(os.path.join(dest_path, member_name))

                if not _is_within_root(dest_path, target):
                    return False

                try:
                    resolved = os.path.realpath(target)
                except OSError:
                    return False

                if not _is_within_root(dest_path, resolved):
                    return False

                if member.isdir():
                    try:
                        os.makedirs(target, exist_ok=True)
                    except OSError:
                        return False
                elif member.isfile():
                    parent = os.path.dirname(target)
                    if parent:
                        try:
                            os.makedirs(parent, exist_ok=True)
                        except OSError:
                            return False
                    source = tf.extractfile(member)
                    if source is None:
                        return False
                    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
                    if hasattr(os, 'O_NOFOLLOW'):
                        flags |= os.O_NOFOLLOW
                    mode = 0o666
                    fd = None
                    fd_closed = False
                    try:
                        fd = os.open(target, flags, mode)
                        with os.fdopen(fd, 'wb') as f:
                            fd_closed = True
                            while True:
                                chunk = source.read(1024 * 1024)
                                if not chunk:
                                    break
                                f.write(chunk)
                    except Exception:
                        if fd is not None and not fd_closed:
                            try:
                                os.close(fd)
                            except OSError:
                                pass
                        return False
                    finally:
                        source.close()
                else:
                    return False
        return True
    except Exception:
        return False
