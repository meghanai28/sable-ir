import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(os.path.normpath(dest_path))
    if not dest_path.endswith(os.sep):
        dest_path_with_sep = dest_path + os.sep
    else:
        dest_path_with_sep = dest_path

    def is_inside(candidate: str) -> bool:
        return candidate == dest_path or candidate.startswith(dest_path_with_sep)

    def validate_member_path(member_name: str) -> str | None:
        stripped = member_name.lstrip('/')
        joined = os.path.join(dest_path, stripped)
        normalized = os.path.abspath(os.path.normpath(joined))
        if normalized == dest_path or not is_inside(normalized):
            return None
        return normalized

    def validate_symlink_target(target: str, symlink_dir: str) -> str | None:
        if os.path.isabs(target):
            normalized = os.path.abspath(os.path.normpath(target))
        else:
            joined = os.path.join(symlink_dir, target)
            normalized = os.path.abspath(os.path.normpath(joined))
        if normalized == dest_path or not is_inside(normalized):
            return None
        return normalized

    try:
        tf = tarfile.open(tar_path, 'r:*')
    except Exception:
        return False

    validated_members = []

    try:
        for member in tf.getmembers():
            if member.issym() or member.islnk() or member.isfile() or member.isdir():
                pass
            else:
                tf.close()
                return False

            validated_path = validate_member_path(member.name)
            if validated_path is None:
                tf.close()
                return False

            if member.issym():
                symlink_dir = os.path.dirname(validated_path)
                validated_target = validate_symlink_target(member.linkname, symlink_dir)
                if validated_target is None:
                    tf.close()
                    return False
                validated_members.append((member, validated_path, member.linkname))

            elif member.islnk():
                validated_target = validate_member_path(member.linkname)
                if validated_target is None:
                    tf.close()
                    return False
                validated_members.append((member, validated_path, validated_target))

            else:
                validated_members.append((member, validated_path, None))

    except Exception:
        tf.close()
        return False

    if os.path.exists(dest_path):
        if not os.path.isdir(dest_path):
            tf.close()
            return False
    else:
        try:
            os.makedirs(dest_path, exist_ok=True)
        except Exception:
            tf.close()
            return False

    for member, validated_path, extra in validated_members:
        try:
            if member.isdir():
                if not os.path.exists(validated_path):
                    os.makedirs(validated_path, exist_ok=True)
                elif not os.path.isdir(validated_path):
                    tf.close()
                    return False

            elif member.isfile():
                parent = os.path.dirname(validated_path)
                current = dest_path
                for component in os.path.relpath(parent, dest_path).split(os.sep):
                    if not component or component == '.':
                        continue
                    current = os.path.join(current, component)
                    if os.path.exists(current):
                        if not os.path.isdir(current) or os.path.islink(current):
                            tf.close()
                            return False
                    else:
                        os.mkdir(current)

                try:
                    fd = os.open(validated_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
                except FileExistsError:
                    tf.close()
                    return False
                except Exception:
                    tf.close()
                    return False

                try:
                    with os.fdopen(fd, 'wb') as f:
                        file_obj = tf.extractfile(member)
                        if file_obj is None:
                            tf.close()
                            return False
                        while True:
                            chunk = file_obj.read(65536)
                            if not chunk:
                                break
                            f.write(chunk)
                except Exception:
                    try:
                        os.close(fd)
                    except Exception:
                        pass
                    tf.close()
                    return False

            elif member.issym():
                os.symlink(extra, validated_path)

            elif member.islnk():
                os.link(extra, validated_path)

        except Exception:
            tf.close()
            return False

    tf.close()
    return True
