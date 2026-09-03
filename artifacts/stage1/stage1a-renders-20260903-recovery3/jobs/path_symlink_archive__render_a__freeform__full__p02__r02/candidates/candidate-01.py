import os
import tarfile
import shutil


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        trusted_root = os.path.abspath(os.path.normpath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()
    except (tarfile.TarError, OSError, IOError):
        return False

    success = True

    for member in members:
        if member.issym() or member.islnk():
            success = False
            continue

        if not (member.isfile() or member.isdir()):
            success = False
            continue

        candidate_path = os.path.join(trusted_root, member.name)
        normalized_path = os.path.abspath(os.path.normpath(candidate_path))

        try:
            common = os.path.commonpath([trusted_root, normalized_path])
        except ValueError:
            success = False
            continue

        if common != trusted_root:
            success = False
            continue

        if normalized_path == trusted_root and not member.isdir():
            success = False
            continue

        try:
            if member.isdir():
                os.makedirs(normalized_path, exist_ok=True)
            elif member.isfile():
                parent_dir = os.path.dirname(normalized_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)

                with tf.extractfile(member) as src:
                    with open(normalized_path, 'wb') as dst:
                        shutil.copyfileobj(src, dst)
        except (OSError, IOError, TypeError, AttributeError):
            success = False
            continue

    return success
