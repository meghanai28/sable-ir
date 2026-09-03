import os
import tarfile


def _is_within(path: str, base: str) -> bool:
    try:
        norm_base = os.path.normpath(os.path.abspath(base))
        norm_path = os.path.normpath(os.path.abspath(path))
        if norm_path == norm_base:
            return True
        return os.path.commonpath([norm_path, norm_base]) == norm_base
    except ValueError:
        return False


def _safe_makedirs(target: str, base: str) -> bool:
    if not _is_within(target, base):
        return False
    norm_base = os.path.normpath(os.path.abspath(base))
    norm_target = os.path.normpath(os.path.abspath(target))
    if norm_target == norm_base:
        return True
    rel = os.path.relpath(norm_target, norm_base)
    current = norm_base
    for part in rel.split(os.sep):
        if part == os.curdir or part == "":
            continue
        current = os.path.join(current, part)
        try:
            os.mkdir(current)
        except FileExistsError:
            if os.path.islink(current) or not os.path.isdir(current):
                return False
        except OSError:
            return False
    return True


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.normpath(os.path.abspath(dest_path))
        os.makedirs(dest_path, exist_ok=True)
        dest_path = os.path.realpath(dest_path)
    except Exception:
        return False

    try:
        with tarfile.open(tar_path, "r:*") as tf:
            members = tf.getmembers()
            symlink_paths = set()

            # First pass: validate member paths and link targets
            for member in members:
                if not member.name:
                    return False

                abs_path = os.path.normpath(os.path.join(dest_path, member.name))

                if not _is_within(abs_path, dest_path):
                    return False

                if abs_path == dest_path and not member.isdir():
                    return False

                if member.issym():
                    target = member.linkname
                    if os.path.isabs(target):
                        target_path = os.path.normpath(target)
                    else:
                        link_dir = os.path.dirname(abs_path)
                        target_path = os.path.normpath(os.path.join(link_dir, target))
                    if not _is_within(target_path, dest_path):
                        return False
                    symlink_paths.add(abs_path)
                elif member.islnk():
                    target = member.linkname
                    if os.path.isabs(target):
                        target_path = os.path.normpath(target)
                    else:
                        target_path = os.path.normpath(os.path.join(dest_path, target))
                    if not _is_within(target_path, dest_path):
                        return False
                elif not (member.isfile() or member.isdir()):
                    return False

            # Second pass: ensure no member path traverses an archive symlink
            for member in members:
                abs_path = os.path.normpath(os.path.join(dest_path, member.name))
                if abs_path == dest_path:
                    continue
                parent = os.path.dirname(abs_path)
                while parent != dest_path:
                    if parent in symlink_paths:
                        return False
                    next_parent = os.path.dirname(parent)
                    if next_parent == parent:
                        break
                    parent = next_parent

            # Third pass: extract
            for member in members:
                abs_path = os.path.normpath(os.path.join(dest_path, member.name))

                if member.isdir():
                    if not _safe_makedirs(abs_path, dest_path):
                        return False
                    try:
                        os.chmod(abs_path, member.mode)
                    except OSError:
                        pass

                elif member.isfile():
                    parent = os.path.dirname(abs_path)
                    if not _safe_makedirs(parent, dest_path):
                        return False
                    if hasattr(os, "O_NOFOLLOW"):
                        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW
                    else:
                        if os.path.islink(abs_path):
                            return False
                        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
                    try:
                        fd = os.open(abs_path, flags, member.mode or 0o644)
                    except OSError:
                        return False
                    with os.fdopen(fd, "wb") as out_f:
                        f = tf.extractfile(member)
                        if f is None:
                            return False
                        while True:
                            chunk = f.read(65536)
                            if not chunk:
                                break
                            out_f.write(chunk)

                elif member.issym():
                    parent = os.path.dirname(abs_path)
                    if not _safe_makedirs(parent, dest_path):
                        return False
                    if os.path.lexists(abs_path):
                        return False
                    try:
                        os.symlink(member.linkname, abs_path)
                    except OSError:
                        return False

                elif member.islnk():
                    parent = os.path.dirname(abs_path)
                    if not _safe_makedirs(parent, dest_path):
                        return False
                    if os.path.lexists(abs_path):
                        return False
                    target = member.linkname
                    if os.path.isabs(target):
                        target_path = os.path.normpath(target)
                    else:
                        target_path = os.path.normpath(os.path.join(dest_path, target))
                    try:
                        os.link(target_path, abs_path)
                    except OSError:
                        return False

            return True
    except Exception:
        return False
