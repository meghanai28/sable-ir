import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.abspath(dest_path)
        os.makedirs(abs_dest, exist_ok=True)
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False

                member_path = os.path.join(abs_dest, member.name)
                try:
                    normalized_path = os.path.normpath(member_path)
                except (OSError, ValueError):
                    return False

                if not normalized_path.startswith(abs_dest + os.sep) and normalized_path != abs_dest:
                    return False

                if member.isfile():
                    try:
                        parent_dir = os.path.dirname(normalized_path)
                        os.makedirs(parent_dir, exist_ok=True)
                    except (OSError, ValueError):
                        return False

                    try:
                        if os.path.islink(normalized_path):
                            return False
                        if os.path.exists(normalized_path) and not os.path.isfile(normalized_path):
                            return False
                    except (OSError, ValueError):
                        return False

                    try:
                        with tar.extractfile(member) as source, open(normalized_path, 'wb') as target:
                            if source is None:
                                return False
                            while True:
                                chunk = source.read(8192)
                                if not chunk:
                                    break
                                target.write(chunk)
                    except (OSError, ValueError, TypeError, tarfile.TarError):
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

        return True
    except (OSError, ValueError, tarfile.TarError):
        return False
