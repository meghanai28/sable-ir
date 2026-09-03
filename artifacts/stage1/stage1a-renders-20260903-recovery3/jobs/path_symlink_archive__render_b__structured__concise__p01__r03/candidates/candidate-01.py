import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.normpath(os.path.abspath(dest_path))
        if not abs_dest.endswith(os.sep):
            abs_dest += os.sep

        if not os.path.exists(abs_dest):
            try:
                os.makedirs(abs_dest, exist_ok=True)
            except OSError:
                return False

        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()

            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    return False

                normalized_member = os.path.normpath(os.path.join(abs_dest, member_name))
                if not normalized_member.startswith(abs_dest):
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                        if not normalized_target.startswith(abs_dest):
                            return False
                    else:
                        member_dir = os.path.dirname(normalized_member)
                        if not member_dir.endswith(os.sep):
                            member_dir += os.sep
                        normalized_target = os.path.normpath(os.path.join(member_dir, link_target))
                        if not normalized_target.startswith(abs_dest):
                            return False

            for member in members:
                member_name = member.name
                normalized_member = os.path.normpath(os.path.join(abs_dest, member_name))

                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        member_dir = os.path.dirname(normalized_member)
                        if not member_dir.endswith(os.sep):
                            member_dir += os.sep
                        normalized_target = os.path.normpath(os.path.join(member_dir, link_target))

                    if not normalized_target.startswith(abs_dest):
                        return False

                try:
                    tf.extract(member, path=abs_dest)
                except (OSError, tarfile.TarError):
                    return False

        return True
    except (OSError, tarfile.TarError):
        return False
