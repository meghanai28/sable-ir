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
                member_path = member.name
                if member_path.startswith('/') or member_path.startswith('\\'):
                    member_path = member_path.lstrip('/\\')

                normalized_member_path = os.path.normpath(member_path)
                if normalized_member_path == '.' or normalized_member_path == '':
                    continue

                if os.path.isabs(normalized_member_path):
                    return False

                final_member_path = os.path.join(dest_path, normalized_member_path)
                real_member_path = os.path.realpath(final_member_path)

                if not real_member_path.startswith(dest_path + os.sep) and real_member_path != dest_path:
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target.startswith('/') or link_target.startswith('\\'):
                        link_target = link_target.lstrip('/\\')

                    normalized_link_target = os.path.normpath(link_target)
                    if os.path.isabs(normalized_link_target):
                        return False

                    if member.issym():
                        link_parent = os.path.dirname(real_member_path)
                        resolved_link_target = os.path.normpath(os.path.join(link_parent, normalized_link_target))
                        real_link_target = os.path.realpath(resolved_link_target)
                    else:
                        resolved_link_target = os.path.normpath(os.path.join(dest_path, normalized_link_target))
                        real_link_target = os.path.realpath(resolved_link_target)

                    if not real_link_target.startswith(dest_path + os.sep) and real_link_target != dest_path:
                        return False

                validated_members.append(member)

            for member in validated_members:
                try:
                    tf.extract(member, path=dest_path)
                except (OSError, tarfile.TarError):
                    return False

            return True

    except (OSError, tarfile.TarError):
        return False
