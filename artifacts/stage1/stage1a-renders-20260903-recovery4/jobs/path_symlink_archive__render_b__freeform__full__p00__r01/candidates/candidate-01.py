import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_abs = os.path.abspath(os.path.normpath(dest_path))
    guard_prefix = dest_abs + os.sep

    def is_inside(candidate: str) -> bool:
        return candidate.startswith(guard_prefix)

    def validate_member_path(member_name: str) -> str | None:
        stripped = member_name.lstrip('/')
        joined = os.path.join(dest_abs, stripped)
        normalized = os.path.normpath(joined)
        if normalized == dest_abs or not is_inside(normalized):
            return None
        return normalized

    def validate_symlink_target(target: str, symlink_dir: str) -> str | None:
        if os.path.isabs(target):
            normalized = os.path.normpath(target)
        else:
            joined = os.path.join(symlink_dir, target)
            normalized = os.path.normpath(joined)
        if normalized == dest_abs or not is_inside(normalized):
            return None
        return normalized

    try:
        tf = tarfile.open(tar_path, 'r:*')
    except Exception:
        return False

    members = tf.getmembers()

    validated_paths = {}
    validated_symlink_targets = {}
    validated_hardlink_targets = {}

    for member in members:
        if member.isdev() or member.isfifo() or not (member.isfile() or member.isdir() or member.issym() or member.islnk()):
            tf.close()
            return False

        member_path = validate_member_path(member.name)
        if member_path is None:
            tf.close()
            return False

        validated_paths[member.name] = member_path

        if member.issym():
            symlink_dir = os.path.dirname(member_path)
            target = member.linkname
            validated_target = validate_symlink_target(target, symlink_dir)
            if validated_target is None:
                tf.close()
                return False
            validated_symlink_targets[member.name] = target

        if member.islnk():
            target_path = validate_member_path(member.linkname)
            if target_path is None:
                tf.close()
                return False
            validated_hardlink_targets[member.name] = target_path

    try:
        if os.path.exists(dest_abs):
            if not os.path.isdir(dest_abs):
                tf.close()
                return False
        else:
            os.makedirs(dest_abs, exist_ok=True)
    except Exception:
        tf.close()
        return False

    for member in members:
        member_path = validated_paths[member.name]

        try:
            if member.isdir():
                if not os.path.exists(member_path):
                    os.makedirs(member_path, exist_ok=True)
                elif not os.path.isdir(member_path):
                    tf.close()
                    return False

            elif member.isfile():
                parent = os.path.dirname(member_path)
                current = dest_abs
                for component in os.path.relpath(parent, dest_abs).split(os.sep):
                    if component == '.' or component == '':
                        continue
                    current = os.path.join(current, component)
                    if os.path.exists(current):
                        if not os.path.isdir(current) or os.path.islink(current):
                            tf.close()
                            return False
                    else:
                        os.mkdir(current)

                fd = os.open(member_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
                try:
                    f = os.fdopen(fd, 'wb')
                    try:
                        with tf.extractfile(member) as src:
                            if src is None:
                                f.close()
                                tf.close()
                                return False
                            while True:
                                chunk = src.read(65536)
                                if not chunk:
                                    break
                                f.write(chunk)
                    finally:
                        f.close()
                except Exception:
                    try:
                        os.close(fd)
                    except Exception:
                        pass
                    tf.close()
                    return False

            elif member.issym():
                os.symlink(validated_symlink_targets[member.name], member_path)

            elif member.islnk():
                target_path = validated_hardlink_targets[member.name]
                os.link(target_path, member_path)

        except Exception:
            tf.close()
            return False

    tf.close()
    return True
