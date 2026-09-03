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
    except (tarfile.TarError, OSError, IOError):
        return False

    validated_members = []
    for member in members:
        member_name = member.name
        if member_name.startswith('/') or member_name.startswith('\\'):
            member_name = member_name[1:]
        if os.path.isabs(member_name):
            return False

        member_path = os.path.join(dest_path, member_name)
        try:
            real_member_path = os.path.realpath(member_path)
        except (OSError, ValueError):
            return False

        if not real_member_path.startswith(dest_path + os.sep) and real_member_path != dest_path:
            return False

        if member.issym() or member.islnk():
            link_target = member.linkname
            if link_target.startswith('/') or link_target.startswith('\\'):
                link_target = link_target[1:]
            if os.path.isabs(link_target):
                return False

            if member.issym():
                resolved_link_target = os.path.join(os.path.dirname(real_member_path), link_target)
            else:
                resolved_link_target = os.path.join(dest_path, link_target)

            try:
                real_link_target = os.path.realpath(resolved_link_target)
            except (OSError, ValueError):
                return False

            if not real_link_target.startswith(dest_path + os.sep) and real_link_target != dest_path:
                return False

        validated_members.append(member)

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in validated_members:
                try:
                    tf.extract(member, path=dest_path)
                except (tarfile.TarError, OSError, IOError):
                    return False
    except (tarfile.TarError, OSError, IOError):
        return False

    return True
