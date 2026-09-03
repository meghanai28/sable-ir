import os
import tarfile


def _is_within(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        return False


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        norm_dest = os.path.normpath(os.path.abspath(dest_path))
        os.makedirs(norm_dest, exist_ok=True)
    except Exception:
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            regular_members = []
            hardlink_members = []

            for member in members:
                if not member.name:
                    if member.isdir():
                        continue
                    return False

                abs_member = os.path.normpath(os.path.join(norm_dest, member.name))

                if abs_member == norm_dest:
                    if not member.isdir():
                        return False
                    continue

                if not _is_within(abs_member, norm_dest):
                    return False

                if member.issym():
                    symlink_dir = os.path.dirname(abs_member)
                    abs_link_target = os.path.normpath(
                        os.path.join(symlink_dir, member.linkname)
                    )
                    if (
                        not _is_within(abs_link_target, norm_dest)
                        and abs_link_target != norm_dest
                    ):
                        return False
                    regular_members.append((abs_member, member))
                elif member.islnk():
                    abs_link_target = os.path.normpath(
                        os.path.join(norm_dest, member.linkname)
                    )
                    if (
                        not _is_within(abs_link_target, norm_dest)
                        and abs_link_target != norm_dest
                    ):
                        return False
                    hardlink_members.append((abs_member, abs_link_target, member))
                elif member.isdir() or member.isreg():
                    regular_members.append((abs_member, member))
                else:
                    return False

            for abs_member, member in regular_members:
                try:
                    parent = os.path.dirname(abs_member)
                    if parent:
                        os.makedirs(parent, exist_ok=True)

                    if member.isdir():
                        os.makedirs(abs_member, exist_ok=True)
                        if member.mode is not None:
                            os.chmod(abs_member, member.mode)
                    elif member.isreg():
                        src = tf.extractfile(member)
                        if src is None:
                            return False
                        with src, open(abs_member, 'wb') as dst:
                            while True:
                                chunk = src.read(65536)
                                if not chunk:
                                    break
                                dst.write(chunk)
                        if member.mode is not None:
                            os.chmod(abs_member, member.mode)
                    elif member.issym():
                        if os.path.lexists(abs_member):
                            os.remove(abs_member)
                        os.symlink(member.linkname, abs_member)
                except Exception:
                    return False

            for abs_member, abs_link_target, member in hardlink_members:
                try:
                    parent = os.path.dirname(abs_member)
                    if parent:
                        os.makedirs(parent, exist_ok=True)
                    if os.path.lexists(abs_member):
                        os.remove(abs_member)
                    os.link(abs_link_target, abs_member)
                except Exception:
                    return False

            return True
    except Exception:
        return False
