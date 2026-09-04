import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.normpath(dest_path))
    if not dest_path.endswith(os.sep):
        dest_path = dest_path + os.sep

    def is_inside(path: str) -> bool:
        return path.startswith(dest_path) and path != dest_path.rstrip(os.sep)

    def validate_member_path(name: str) -> str | None:
        name = name.lstrip('/')
        full_path = os.path.abspath(os.path.normpath(os.path.join(dest_path, name)))
        if full_path == dest_path.rstrip(os.sep) or not is_inside(full_path):
            return None
        return full_path

    def validate_symlink_target(target: str, symlink_dir: str) -> str | None:
        if os.path.isabs(target):
            resolved = os.path.abspath(os.path.normpath(target))
        else:
            resolved = os.path.abspath(os.path.normpath(os.path.join(symlink_dir, target)))
        if resolved == dest_path.rstrip(os.sep) or not is_inside(resolved):
            return None
        return resolved

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = list(tf.getmembers())

            validated_paths = {}
            for member in members:
                if member.isdev() or member.isfifo() or not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
                    return False

                member_path = validate_member_path(member.name)
                if member_path is None:
                    return False

                if member.issym():
                    symlink_dir = os.path.dirname(member_path)
                    if validate_symlink_target(member.linkname, symlink_dir) is None:
                        return False

                if member.islnk():
                    target_path = validate_member_path(member.linkname)
                    if target_path is None:
                        return False

                validated_paths[member.name] = member_path

            if not os.path.exists(dest_path):
                os.makedirs(dest_path)
            elif not os.path.isdir(dest_path):
                return False

            for member in members:
                member_path = validated_paths[member.name]

                if member.isdir():
                    if not os.path.exists(member_path):
                        os.makedirs(member_path)
                    elif not os.path.isdir(member_path):
                        return False

                elif member.isfile():
                    parent = os.path.dirname(member_path)
                    current = dest_path.rstrip(os.sep)
                    for component in os.path.relpath(parent, current).split(os.sep):
                        if component == '.' or component == '':
                            continue
                        current = os.path.join(current, component)
                        if os.path.exists(current):
                            if not os.path.isdir(current) or os.path.islink(current):
                                return False
                        else:
                            os.mkdir(current)

                    try:
                        fd = os.open(member_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
                        with os.fdopen(fd, 'wb') as f:
                            with tf.extractfile(member) as src:
                                if src is None:
                                    return False
                                while True:
                                    chunk = src.read(65536)
                                    if not chunk:
                                        break
                                    f.write(chunk)
                    except (OSError, IOError, TypeError):
                        return False

                elif member.issym():
                    try:
                        os.symlink(member.linkname, member_path)
                    except (OSError, IOError):
                        return False

                elif member.islnk():
                    target_path = validated_paths.get(member.linkname)
                    if target_path is None:
                        target_path = validate_member_path(member.linkname)
                        if target_path is None:
                            return False
                    try:
                        os.link(target_path, member_path)
                    except (OSError, IOError):
                        return False

            return True

    except (tarfile.TarError, OSError, IOError):
        return False
