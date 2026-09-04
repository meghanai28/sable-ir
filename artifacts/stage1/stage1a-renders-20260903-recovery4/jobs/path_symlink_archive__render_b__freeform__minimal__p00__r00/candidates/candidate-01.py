import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.abspath(os.path.realpath(dest_path))
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

                target_path = os.path.join(abs_dest, member_name)
                norm_target = os.path.normpath(target_path)

                try:
                    real_target = os.path.realpath(target_path)
                except (OSError, ValueError):
                    return False

                if not (norm_target == abs_dest or norm_target.startswith(abs_dest + os.sep) or real_target == abs_dest or real_target.startswith(abs_dest + os.sep)):
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if link_target is None:
                        return False

                    if os.path.isabs(link_target):
                        resolved_link = os.path.normpath(link_target)
                    else:
                        parent_dir = os.path.dirname(target_path)
                        resolved_link = os.path.normpath(os.path.join(parent_dir, link_target))

                    try:
                        real_link = os.path.realpath(resolved_link)
                    except (OSError, ValueError):
                        return False

                    if not (resolved_link == abs_dest or resolved_link.startswith(abs_dest + os.sep) or real_link == abs_dest or real_link.startswith(abs_dest + os.sep)):
                        return False

                validated.append((member, target_path))

            for member, target_path in validated:
                parent = os.path.dirname(target_path)
                try:
                    os.makedirs(parent, exist_ok=True)
                except (OSError, ValueError):
                    return False

                if member.isdir():
                    try:
                        os.makedirs(target_path, exist_ok=True)
                    except (OSError, ValueError):
                        return False
                elif member.isfile():
                    try:
                        with tf.extractfile(member) as src:
                            if src is None:
                                return False
                            with open(target_path, 'wb') as dst:
                                while True:
                                    chunk = src.read(65536)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
                        os.chmod(target_path, member.mode)
                    except (OSError, ValueError, TypeError):
                        return False
                elif member.issym():
                    try:
                        os.symlink(member.linkname, target_path)
                    except (OSError, ValueError):
                        return False
                elif member.islnk():
                    try:
                        os.link(member.linkname, target_path)
                    except (OSError, ValueError):
                        return False
                else:
                    continue

            return True
    except (tarfile.TarError, OSError, ValueError):
        return False
