import os
import tarfile
import stat

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
    except (tarfile.TarError, OSError, IOError):
        return False

    validated_members = []

    for member in members:
        member_name = member.name

        if os.path.isabs(member_name):
            return False

        joined_path = os.path.join(dest_path, member_name)
        try:
            normalized_member_path = os.path.normpath(os.path.abspath(joined_path))
        except (OSError, ValueError):
            return False

        if not normalized_member_path.startswith(dest_path + os.sep) and normalized_member_path != dest_path:
            return False

        if member.issym() or member.islnk():
            link_target = member.linkname

            if os.path.isabs(link_target):
                normalized_link_target = os.path.normpath(os.path.abspath(link_target))
            else:
                link_parent = os.path.dirname(normalized_member_path)
                joined_link_target = os.path.join(link_parent, link_target)
                try:
                    normalized_link_target = os.path.normpath(os.path.abspath(joined_link_target))
                except (OSError, ValueError):
                    return False

            if not normalized_link_target.startswith(dest_path + os.sep) and normalized_link_target != dest_path:
                return False

        validated_members.append((member, normalized_member_path))

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member, normalized_member_path in validated_members:
                if member.isdir():
                    os.makedirs(normalized_member_path, exist_ok=True)
                    try:
                        os.utime(normalized_member_path, (member.mtime, member.mtime), follow_symlinks=False)
                    except (OSError, IOError):
                        pass
                elif member.isfile():
                    parent_dir = os.path.dirname(normalized_member_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)

                    fd = os.open(normalized_member_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
                    try:
                        fobj = tf.extractfile(member)
                        if fobj is not None:
                            try:
                                while True:
                                    chunk = fobj.read(65536)
                                    if not chunk:
                                        break
                                    os.write(fd, chunk)
                            finally:
                                fobj.close()
                    finally:
                        os.close(fd)

                    mode = member.mode
                    if mode:
                        os.chmod(normalized_member_path, stat.S_IMODE(mode))
                    try:
                        os.utime(normalized_member_path, (member.mtime, member.mtime), follow_symlinks=False)
                    except (OSError, IOError):
                        pass
                elif member.issym():
                    parent_dir = os.path.dirname(normalized_member_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    os.symlink(member.linkname, normalized_member_path)
                    try:
                        os.lutime(normalized_member_path, (member.mtime, member.mtime))
                    except (AttributeError, OSError, IOError):
                        pass
                elif member.islnk():
                    parent_dir = os.path.dirname(normalized_member_path)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                    source_path = os.path.normpath(os.path.abspath(os.path.join(os.path.dirname(normalized_member_path), member.linkname)))
                    os.link(source_path, normalized_member_path)
                    try:
                        os.utime(normalized_member_path, (member.mtime, member.mtime), follow_symlinks=False)
                    except (OSError, IOError):
                        pass

        return True
    except (OSError, IOError, tarfile.TarError):
        return False
