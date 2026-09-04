import os
import tarfile
from typing import Optional


def _resolve_safe_path(dest_path: str, member_name: str) -> Optional[str]:
    dest_abs = os.path.abspath(os.path.realpath(dest_path))
    member_abs = os.path.abspath(os.path.join(dest_abs, member_name))
    try:
        real_member = os.path.realpath(member_abs)
    except (OSError, ValueError):
        return None
    if not real_member.startswith(dest_abs + os.sep) and real_member != dest_abs:
        return None
    return real_member


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_abs = os.path.abspath(os.path.realpath(dest_path))
    try:
        os.makedirs(dest_abs, exist_ok=True)
    except (OSError, ValueError):
        return False
    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            for member in tf:
                if member.issym() or member.islnk():
                    return False
                safe_path = _resolve_safe_path(dest_abs, member.name)
                if safe_path is None:
                    return False
                if member.isfile():
                    try:
                        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
                    except (OSError, ValueError):
                        return False
                    try:
                        with tf.extractfile(member) as fobj:
                            if fobj is None:
                                return False
                            with open(safe_path, 'wb') as out:
                                while True:
                                    chunk = fobj.read(65536)
                                    if not chunk:
                                        break
                                    out.write(chunk)
                    except (OSError, ValueError, TypeError):
                        return False
                elif member.isdir():
                    try:
                        os.makedirs(safe_path, exist_ok=True)
                    except (OSError, ValueError):
                        return False
                else:
                    return False
        return True
    except (tarfile.TarError, OSError, ValueError):
        return False
