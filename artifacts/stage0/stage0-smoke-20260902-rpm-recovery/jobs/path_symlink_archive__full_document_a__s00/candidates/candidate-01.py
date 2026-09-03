import os
import tarfile
import stat


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.realpath(dest_path)
        if not os.path.isdir(dest_path):
            return False

        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf.getmembers():
                member_name = member.name
                if member_name.startswith('/') or '..' in member_name.split('/'):
                    return False

                if member.issym() or member.islnk():
                    return False

                if not (member.isfile() or member.isdir()):
                    return False

                extract_path = os.path.realpath(os.path.join(dest_path, member_name))
                if not extract_path.startswith(dest_path + os.sep) and extract_path != dest_path:
                    return False

            for member in tf.getmembers():
                member_name = member.name
                extract_path = os.path.realpath(os.path.join(dest_path, member_name))

                if member.isdir():
                    os.makedirs(extract_path, exist_ok=True)
                    continue

                if member.isfile():
                    parent_dir = os.path.dirname(extract_path)
                    os.makedirs(parent_dir, exist_ok=True)

                    if member.mode & (stat.S_ISUID | stat.S_ISGID):
                        mode = member.mode & ~(stat.S_ISUID | stat.S_ISGID)
                    else:
                        mode = member.mode

                    with tf.extractfile(member) as src:
                        if src is None:
                            return False
                        with open(extract_path, 'wb') as dst:
                            while True:
                                chunk = src.read(65536)
                                if not chunk:
                                    break
                                dst.write(chunk)

                    os.chmod(extract_path, mode)

        return True

    except Exception:
        return False
