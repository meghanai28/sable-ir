import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_abs = os.path.abspath(os.path.realpath(dest_path))
        if not os.path.isdir(dest_abs):
            try:
                os.makedirs(dest_abs, exist_ok=True)
            except OSError:
                return False

        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()

            validated_members = []
            for member in members:
                if member.issym() or member.islnk():
                    return False

                if not (member.isfile() or member.isdir()):
                    if member.isdev() or member.isfifo() or member.ischr() or member.isblk():
                        return False
                    continue

                member_path = member.name
                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')
                    if not member_path:
                        continue

                joined_path = os.path.join(dest_abs, member_path)
                resolved_path = os.path.abspath(os.path.realpath(joined_path))

                if resolved_path == dest_abs:
                    pass
                elif not (resolved_path == dest_abs or resolved_path.startswith(dest_abs + os.sep)):
                    return False

                validated_members.append((member, resolved_path))

            for member, resolved_path in validated_members:
                if member.isdir():
                    try:
                        os.makedirs(resolved_path, exist_ok=True)
                    except OSError:
                        return False
                elif member.isfile():
                    parent_dir = os.path.dirname(resolved_path)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except OSError:
                        return False

                    try:
                        with tf.extractfile(member) as src:
                            if src is None:
                                return False
                            with open(resolved_path, 'wb') as dst:
                                while True:
                                    chunk = src.read(65536)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
                    except (OSError, IOError, tarfile.TarError):
                        return False

                    try:
                        mode = member.mode
                        if mode is not None:
                            os.chmod(resolved_path, mode)
                    except OSError:
                        pass

        return True
    except (tarfile.TarError, OSError, IOError):
        return False
