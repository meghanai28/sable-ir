import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_real = os.path.realpath(dest_path)
        if not os.path.isdir(dest_real):
            return False
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            validated_members = []

            for member in members:
                entry_path = member.name
                try:
                    normalized_entry = os.path.normpath(entry_path)
                except (ValueError, OSError):
                    return False

                if os.path.isabs(normalized_entry):
                    normalized_entry = normalized_entry.lstrip('/')
                    if not normalized_entry:
                        normalized_entry = '.'

                full_entry = os.path.join(dest_real, normalized_entry)
                try:
                    real_entry = os.path.realpath(full_entry)
                except (OSError, ValueError):
                    return False

                if not (real_entry == dest_real or real_entry.startswith(dest_real + os.sep)):
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname
                    try:
                        normalized_target = os.path.normpath(link_target)
                    except (ValueError, OSError):
                        return False

                    if os.path.isabs(normalized_target):
                        full_target = os.path.normpath(normalized_target)
                        try:
                            real_target = os.path.realpath(full_target)
                        except (OSError, ValueError):
                            return False
                    else:
                        parent_dir = os.path.dirname(full_entry)
                        full_target = os.path.join(parent_dir, normalized_target)
                        try:
                            real_target = os.path.realpath(full_target)
                        except (OSError, ValueError):
                            return False

                    if not (real_target == dest_real or real_target.startswith(dest_real + os.sep)):
                        return False

                validated_members.append(member)

            for member in validated_members:
                try:
                    tf.extract(member, path=dest_real)
                except (tarfile.TarError, OSError, IOError):
                    return False

            return True

    except (tarfile.TarError, OSError, IOError):
        return False
