import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.realpath(dest_path))
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

                if os.path.isabs(member_path):
                    return False

                joined_path = os.path.join(dest_path, member_path)
                try:
                    normalized_path = os.path.normpath(joined_path)
                    real_path = os.path.realpath(normalized_path)
                except (OSError, ValueError):
                    return False

                if not real_path.startswith(dest_path + os.sep) and real_path != dest_path:
                    return False

                validated_members.append((member, real_path))

            for member, real_path in validated_members:
                if member.issym() or member.islnk():
                    return False

                if member.isfile():
                    parent_dir = os.path.dirname(real_path)
                    try:
                        parent_real = os.path.realpath(parent_dir)
                        if not parent_real.startswith(dest_path + os.sep) and parent_real != dest_path:
                            return False
                    except (OSError, ValueError):
                        return False

                    if not os.path.exists(parent_dir):
                        try:
                            os.makedirs(parent_dir, exist_ok=True)
                        except OSError:
                            return False

                    try:
                        with tf.extractfile(member) as source:
                            if source is None:
                                return False
                            with open(real_path, 'wb') as target:
                                while True:
                                    chunk = source.read(8192)
                                    if not chunk:
                                        break
                                    target.write(chunk)
                        os.utime(real_path, (member.mtime, member.mtime))
                        os.chmod(real_path, member.mode)
                    except (OSError, IOError, tarfile.TarError):
                        return False

                elif member.isdir():
                    try:
                        os.makedirs(real_path, exist_ok=True)
                        os.utime(real_path, (member.mtime, member.mtime))
                        os.chmod(real_path, member.mode)
                    except OSError:
                        return False

                else:
                    return False

    except (tarfile.TarError, OSError, IOError):
        return False

    return True
