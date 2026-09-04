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
                if member.issym() or member.islnk():
                    return False

                if not (member.isfile() or member.isdir()):
                    continue

                member_path = member.name

                if os.path.isabs(member_path):
                    return False

                normalized = os.path.normpath(member_path)
                if normalized.startswith('..') or normalized == '..':
                    return False

                full_path = os.path.join(dest_path, normalized)
                full_path = os.path.abspath(os.path.realpath(full_path))

                try:
                    real_dest = os.path.realpath(dest_path)
                    real_full = os.path.realpath(full_path)
                except (OSError, ValueError):
                    return False

                if not (real_full == real_dest or real_full.startswith(real_dest + os.sep)):
                    return False

                validated_members.append((member, full_path))

            for member, full_path in validated_members:
                try:
                    if member.isdir():
                        os.makedirs(full_path, exist_ok=True)
                    elif member.isfile():
                        parent_dir = os.path.dirname(full_path)
                        os.makedirs(parent_dir, exist_ok=True)
                        with tf.extractfile(member) as fobj:
                            if fobj is None:
                                return False
                            with open(full_path, 'wb') as out_f:
                                while True:
                                    chunk = fobj.read(65536)
                                    if not chunk:
                                        break
                                    out_f.write(chunk)
                except (OSError, IOError, tarfile.TarError, AttributeError):
                    return False

            return True
    except (OSError, IOError, tarfile.TarError):
        return False
