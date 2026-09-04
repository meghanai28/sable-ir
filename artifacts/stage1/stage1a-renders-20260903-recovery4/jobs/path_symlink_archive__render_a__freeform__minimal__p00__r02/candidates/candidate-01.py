import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.abspath(dest_path)
        os.makedirs(abs_dest, exist_ok=True)
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                if member.issym() or member.islnk():
                    return False

                member_path = os.path.join(abs_dest, member.name)
                try:
                    normalized_path = os.path.normpath(member_path)
                except (OSError, ValueError):
                    return False

                if os.path.isabs(member.name):
                    return False

                try:
                    real_normalized = os.path.realpath(normalized_path)
                    real_dest = os.path.realpath(abs_dest)
                except (OSError, ValueError):
                    return False

                if not (real_normalized == real_dest or real_normalized.startswith(real_dest + os.sep)):
                    return False

                if member.isfile():
                    try:
                        parent_dir = os.path.dirname(normalized_path)
                        os.makedirs(parent_dir, exist_ok=True)
                        
                        try:
                            parent_real = os.path.realpath(parent_dir)
                            if not (parent_real == real_dest or parent_real.startswith(real_dest + os.sep)):
                                return False
                        except (OSError, ValueError):
                            return False

                        if os.path.islink(normalized_path):
                            return False

                        with tf.extractfile(member) as src_f:
                            if src_f is None:
                                return False
                            with open(normalized_path, 'wb') as dst_f:
                                while True:
                                    chunk = src_f.read(65536)
                                    if not chunk:
                                        break
                                    dst_f.write(chunk)
                    except (OSError, ValueError, TypeError):
                        return False

                elif member.isdir():
                    try:
                        os.makedirs(normalized_path, exist_ok=True)
                    except (OSError, ValueError):
                        return False

                else:
                    return False

        return True
    except (tarfile.TarError, OSError, ValueError):
        return False
