import os
import tarfile
from pathlib import Path


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_real = os.path.realpath(dest_path)
        if not os.path.exists(dest_real):
            os.makedirs(dest_real, exist_ok=True)
        elif not os.path.isdir(dest_real):
            return False
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            validated_members = []

            for member in members:
                if member.issym() or member.islnk():
                    return False

                if not (member.isfile() or member.isdir()):
                    return False

                member_name = member.name
                if os.path.isabs(member_name):
                    member_name = member_name.lstrip('/')
                    if not member_name:
                        return False

                joined_path = os.path.join(dest_real, member_name)
                try:
                    normalized_path = os.path.realpath(joined_path)
                except (OSError, ValueError):
                    return False

                if not normalized_path.startswith(dest_real + os.sep) and normalized_path != dest_real:
                    return False

                validated_members.append((member, normalized_path))

            for member, normalized_path in validated_members:
                if member.isdir():
                    try:
                        os.makedirs(normalized_path, exist_ok=True)
                    except OSError:
                        return False
                elif member.isfile():
                    try:
                        parent_dir = os.path.dirname(normalized_path)
                        os.makedirs(parent_dir, exist_ok=True)
                        with tf.extractfile(member) as fobj:
                            if fobj is None:
                                return False
                            data = fobj.read()
                        with open(normalized_path, 'wb') as out_f:
                            out_f.write(data)
                        if member.mode is not None:
                            try:
                                os.chmod(normalized_path, member.mode)
                            except OSError:
                                pass
                    except (OSError, IOError, tarfile.TarError):
                        return False

        return True
    except (OSError, tarfile.TarError):
        return False
