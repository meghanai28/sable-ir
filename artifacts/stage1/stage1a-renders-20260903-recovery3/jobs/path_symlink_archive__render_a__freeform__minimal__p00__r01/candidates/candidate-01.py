import os
import tarfile

def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_abs = os.path.abspath(dest_path)
        os.makedirs(dest_abs, exist_ok=True)
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False

                member_path = os.path.join(dest_abs, member.name)
                try:
                    normalized_path = os.path.normpath(member_path)
                except (OSError, ValueError):
                    return False

                if not normalized_path.startswith(dest_abs + os.sep) and normalized_path != dest_abs:
                    return False

                if member.isfile():
                    try:
                        parent_dir = os.path.dirname(normalized_path)
                        os.makedirs(parent_dir, exist_ok=True)

                        if os.path.islink(normalized_path) or os.path.islink(parent_dir):
                            return False

                        with tar.extractfile(member) as f:
                            if f is None:
                                return False
                            data = f.read()

                        if os.path.islink(normalized_path) or os.path.islink(os.path.dirname(normalized_path)):
                            return False

                        with open(normalized_path, 'wb') as out_f:
                            out_f.write(data)
                    except (OSError, IOError, ValueError):
                        return False
                elif member.isdir():
                    try:
                        if os.path.islink(normalized_path):
                            return False
                        os.makedirs(normalized_path, exist_ok=True)
                    except (OSError, ValueError):
                        return False
                else:
                    return False
    except (tarfile.TarError, OSError, IOError):
        return False

    return True
