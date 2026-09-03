import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.normpath(os.path.abspath(dest_path))
        if not abs_dest.endswith(os.sep):
            abs_dest += os.sep

        if not os.path.exists(abs_dest.rstrip(os.sep)):
            try:
                os.makedirs(abs_dest.rstrip(os.sep), exist_ok=True)
            except OSError:
                return False

        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()

            for member in members:
                member_name = member.name

                if os.path.isabs(member_name):
                    return False

                if '..' in member_name.split(os.sep) and any(
                    part == '..' for part in member_name.split(os.sep)
                ):
                    member_name = os.path.normpath(member_name)
                    if member_name.startswith('..'):
                        return False
                else:
                    member_name = os.path.normpath(member_name)

                if member_name.startswith('..') or os.path.isabs(member_name):
                    return False

                member_path = os.path.normpath(os.path.join(abs_dest.rstrip(os.sep), member_name))
                if not member_path.endswith(os.sep):
                    member_path += os.sep

                if not member_path.startswith(abs_dest):
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname

                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        member_dir = os.path.dirname(os.path.normpath(os.path.join(abs_dest.rstrip(os.sep), member_name)))
                        normalized_target = os.path.normpath(os.path.join(member_dir, link_target))

                    if not normalized_target.endswith(os.sep):
                        normalized_target += os.sep

                    if not normalized_target.startswith(abs_dest):
                        return False

            for member in members:
                member_name = member.name

                if os.path.isabs(member_name):
                    return False

                if '..' in member_name.split(os.sep) and any(
                    part == '..' for part in member_name.split(os.sep)
                ):
                    member_name = os.path.normpath(member_name)
                    if member_name.startswith('..'):
                        return False
                else:
                    member_name = os.path.normpath(member_name)

                if member_name.startswith('..') or os.path.isabs(member_name):
                    return False

                member_path = os.path.normpath(os.path.join(abs_dest.rstrip(os.sep), member_name))
                if not member_path.endswith(os.sep):
                    member_path += os.sep

                if not member_path.startswith(abs_dest):
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname

                    if os.path.isabs(link_target):
                        normalized_target = os.path.normpath(link_target)
                    else:
                        member_dir = os.path.dirname(os.path.normpath(os.path.join(abs_dest.rstrip(os.sep), member_name)))
                        normalized_target = os.path.normpath(os.path.join(member_dir, link_target))

                    if not normalized_target.endswith(os.sep):
                        normalized_target += os.sep

                    if not normalized_target.startswith(abs_dest):
                        return False

            for member in members:
                try:
                    tf.extract(member, path=abs_dest.rstrip(os.sep), set_attrs=False)
                except (OSError, tarfile.TarError, IOError):
                    return False

        return True

    except (OSError, tarfile.TarError, IOError):
        return False
