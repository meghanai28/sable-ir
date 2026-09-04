import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        trusted_root = os.path.abspath(os.path.normpath(dest_path))
    except Exception:
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
            for member in members:
                if member.issym() or member.islnk():
                    return False

                if member.isfile() or member.isdir():
                    candidate_path = os.path.join(trusted_root, member.name)
                    normalized_path = os.path.abspath(os.path.normpath(candidate_path))

                    try:
                        common = os.path.commonpath([trusted_root, normalized_path])
                    except ValueError:
                        return False

                    if common != trusted_root:
                        return False

                    if normalized_path == trusted_root and not member.isdir():
                        return False

                    if member.isdir():
                        os.makedirs(normalized_path, exist_ok=True)
                    else:
                        parent_dir = os.path.dirname(normalized_path)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)

                        source = tf.extractfile(member)
                        if source is None:
                            return False

                        with open(normalized_path, 'wb') as dest_file:
                            while True:
                                chunk = source.read(65536)
                                if not chunk:
                                    break
                                dest_file.write(chunk)
                            source.close()
                else:
                    return False

            return True
    except Exception:
        return False
