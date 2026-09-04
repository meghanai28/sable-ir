import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.abspath(os.path.normpath(dest_path))
        os.makedirs(abs_dest, exist_ok=True)
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            validated = []

            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        continue

                abs_member_path = os.path.abspath(os.path.normpath(os.path.join(abs_dest, member_name)))

                if not abs_member_path.startswith(abs_dest + os.sep) and abs_member_path != abs_dest:
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target is None:
                        return False

                    if os.path.isabs(link_target):
                        abs_link_target = os.path.abspath(os.path.normpath(link_target))
                    else:
                        abs_link_target = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(abs_member_path), link_target)))

                    if not abs_link_target.startswith(abs_dest + os.sep) and abs_link_target != abs_dest:
                        return False

                validated.append(member)

            for member in validated:
                tf.extract(member, abs_dest)

            return True

    except (tarfile.TarError, OSError, ValueError):
        return False
