import os
import tarfile
import tempfile

def _is_under(path: str, base: str) -> bool:
    try:
        common = os.path.commonpath([os.path.normpath(path), os.path.normpath(base)])
    except ValueError:
        return False
    return common == os.path.normpath(base)

def _ensure_dir(path: str, real_dest: str) -> bool:
    parent = os.path.dirname(path)
    if not _is_under(parent, real_dest):
        return False
    rel = os.path.relpath(parent, real_dest)
    if rel == '.':
        return True
    current = real_dest
    for part in rel.split(os.sep):
        if not part or part == '.':
            continue
        current = os.path.join(current, part)
        if os.path.lexists(current):
            if os.path.islink(current):
                return False
            if not os.path.isdir(current):
                return False
        else:
            try:
                os.mkdir(current)
            except Exception:
                return False
    return True

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    if not os.path.isfile(tar_path):
        return False
    try:
        os.makedirs(dest_path, exist_ok=True)
        real_dest = os.path.realpath(os.path.abspath(dest_path))
        if not os.path.isdir(real_dest):
            return False
    except Exception:
        return False
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            for member in members:
                if member.issym() or member.islnk():
                    return False
                if not member.isfile() and not member.isdir():
                    return False
                if os.path.isabs(member.name):
                    return False
                target_path = os.path.normpath(os.path.join(real_dest, member.name))
                if not _is_under(target_path, real_dest):
                    return False
            for member in members:
                target_path = os.path.normpath(os.path.join(real_dest, member.name))
                if member.isdir():
                    if not _ensure_dir(target_path, real_dest):
                        return False
                    if os.path.lexists(target_path):
                        if os.path.islink(target_path):
                            return False
                        if not os.path.isdir(target_path):
                            return False
                    else:
                        try:
                            os.mkdir(target_path)
                        except Exception:
                            return False
                    if not _is_under(os.path.realpath(target_path), real_dest):
                        return False
                else:
                    if not _ensure_dir(target_path, real_dest):
                        return False
                    fd = -1
                    temp_path = None
                    try:
                        fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(target_path))
                        with os.fdopen(fd, 'wb') as dst:
                            src = tf.extractfile(member)
                            if src is None:
                                raise ValueError('extractfile returned None')
                            while True:
                                chunk = src.read(1024 * 1024)
                                if not chunk:
                                    break
                                dst.write(chunk)
                        os.replace(temp_path, target_path)
                    except Exception:
                        if fd != -1:
                            try:
                                os.close(fd)
                            except Exception:
                                pass
                        if temp_path is not None:
                            try:
                                os.remove(temp_path)
                            except Exception:
                                pass
                        return False
            return True
    except Exception:
        return False
