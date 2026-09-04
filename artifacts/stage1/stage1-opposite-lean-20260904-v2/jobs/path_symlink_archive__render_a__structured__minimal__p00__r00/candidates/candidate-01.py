import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_abs = os.path.abspath(os.path.realpath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()

            validated_members = []

            for member in members:
                member_path = member.name
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        if member.issym() or member.islnk():
                            pass
                        else:
                            continue

                extract_path = os.path.join(dest_abs, member_path)
                extract_path = os.path.abspath(os.path.realpath(extract_path))

                if not extract_path.startswith(dest_abs + os.sep) and extract_path != dest_abs:
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        link_target = link_target.lstrip('/')
                        if not link_target:
                            return False

                    target_path = os.path.join(dest_abs, link_target)
                    target_path = os.path.abspath(os.path.realpath(target_path))

                    if not target_path.startswith(dest_abs + os.sep) and target_path != dest_abs:
                        return False

                validated_members.append(member)

            for member in validated_members:
                tf.extract(member, path=dest_abs)

            return True

    except (tarfile.TarError, OSError, IOError, ValueError):
        return False
