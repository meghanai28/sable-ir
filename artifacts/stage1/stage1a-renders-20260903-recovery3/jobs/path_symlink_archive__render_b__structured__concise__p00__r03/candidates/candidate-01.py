import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.realpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False

    if not os.path.isdir(dest_path):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()

            validated_members = []
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    return False

                member_path = os.path.normpath(member_name)
                if member_path.startswith('..') or member_path.startswith('../'):
                    return False

                full_member_path = os.path.realpath(os.path.join(dest_path, member_path))
                if not full_member_path.startswith(dest_path + os.sep) and full_member_path != dest_path:
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target is None:
                        return False

                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                        if normalized_target == '/' or normalized_target.startswith('..') or normalized_target.startswith('../'):
                            return False
                        full_target = os.path.realpath(os.path.join(dest_path, normalized_target.lstrip('/')))
                    else:
                        normalized_target = os.path.normpath(link_target)
                        if normalized_target.startswith('..') or normalized_target.startswith('../'):
                            return False
                        member_dir = os.path.dirname(full_member_path)
                        full_target = os.path.realpath(os.path.join(member_dir, normalized_target))

                    if not full_target.startswith(dest_path + os.sep) and full_target != dest_path:
                        return False

                validated_members.append((member, full_member_path))

            for member, full_member_path in validated_members:
                try:
                    tf.extract(member, path=dest_path)
                except (OSError, tarfile.TarError):
                    return False

            return True

    except (OSError, tarfile.TarError, ValueError):
        return False
