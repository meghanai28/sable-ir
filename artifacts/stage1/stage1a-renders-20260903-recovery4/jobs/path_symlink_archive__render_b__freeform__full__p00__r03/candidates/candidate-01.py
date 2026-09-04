import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.normpath(dest_path))
    if not dest_path.endswith(os.sep):
        dest_path += os.sep

    def is_inside(candidate: str) -> bool:
        return candidate.startswith(dest_path) and candidate != dest_path.rstrip(os.sep)

    def validate_member_path(name: str) -> str | None:
        if name.startswith('/'):
            name = name.lstrip('/')
        if not name:
            return None
        normalized = os.path.abspath(os.path.normpath(os.path.join(dest_path, name)))
        if normalized == dest_path.rstrip(os.sep) or not is_inside(normalized):
            return None
        return normalized

    def validate_symlink_target(target: str, symlink_dir: str) -> str | None:
        if target.startswith('/'):
            normalized = os.path.abspath(os.path.normpath(target))
        else:
            normalized = os.path.abspath(os.path.normpath(os.path.join(symlink_dir, target)))
        if normalized == dest_path.rstrip(os.sep) or not is_inside(normalized):
            return None
        return normalized

    try:
        tf = tarfile.open(tar_path, 'r:*')
    except Exception:
        return False

    validated_members = []
    members = tf.getmembers()

    for member in members:
        if member.issym() or member.islnk() or member.isreg() or member.isdir():
            pass
        else:
            tf.close()
            return False

        member_path = validate_member_path(member.name)
        if member_path is None:
            tf.close()
            return False

        if member.issym():
            symlink_dir = os.path.dirname(member_path)
            if validate_symlink_target(member.linkname, symlink_dir) is None:
                tf.close()
                return False

        if member.islnk():
            target_path = validate_member_path(member.linkname)
            if target_path is None:
                tf.close()
                return False

        validated_members.append((member, member_path))

    if os.path.exists(dest_path.rstrip(os.sep)):
        if not os.path.isdir(dest_path.rstrip(os.sep)):
            tf.close()
            return False
    else:
        try:
            os.makedirs(dest_path.rstrip(os.sep), exist_ok=True)
        except Exception:
            tf.close()
            return False

    for member, member_path in validated_members:
        try:
            if member.isdir():
                if not os.path.exists(member_path):
                    os.makedirs(member_path, exist_ok=True)
                elif not os.path.isdir(member_path):
                    tf.close()
                    return False

            elif member.isreg():
                parent = os.path.dirname(member_path)
                current = dest_path.rstrip(os.sep)
                for part in os.path.relpath(parent, current).split(os.sep):
                    if part == '.' or part == '':
                        continue
                    current = os.path.join(current, part)
                    if os.path.exists(current):
                        if not os.path.isdir(current) or os.path.islink(current):
                            tf.close()
                            return False
                    else:
                        os.mkdir(current)

                fd = os.open(member_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
                try:
                    f = os.fdopen(fd, 'wb')
                    fobj = tf.extractfile(member)
                    if fobj is not None:
                        while True:
                            chunk = fobj.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                    f.close()
                except Exception:
                    try:
                        os.close(fd)
                    except Exception:
                        pass
                    tf.close()
                    return False

            elif member.issym():
                os.symlink(member.linkname, member_path)

            elif member.islnk():
                target_path = validate_member_path(member.linkname)
                os.link(target_path, member_path)

        except Exception:
            tf.close()
            return False

    tf.close()
    return True
