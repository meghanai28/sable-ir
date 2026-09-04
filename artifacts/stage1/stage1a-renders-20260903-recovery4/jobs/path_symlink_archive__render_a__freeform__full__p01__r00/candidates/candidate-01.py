import os
import tarfile
from pathlib import Path


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        canonical_dest = os.path.realpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False

    success = True

    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    success = False
                    continue

                if not (member.isfile() or member.isdir()):
                    success = False
                    continue

                member_name = member.name

                while member_name.startswith('/') or member_name.startswith('\\'):
                    member_name = member_name[1:]

                if len(member_name) >= 2 and member_name[1] == ':':
                    if member_name[0].isalpha():
                        member_name = member_name[2:]
                        while member_name.startswith('/') or member_name.startswith('\\'):
                            member_name = member_name[1:]

                candidate = os.path.join(canonical_dest, member_name)
                try:
                    normalized = os.path.normpath(os.path.abspath(candidate))
                except (OSError, ValueError):
                    success = False
                    continue

                if normalized == canonical_dest:
                    validated_path = normalized
                else:
                    prefix = canonical_dest + os.sep
                    if not (normalized.startswith(prefix) and len(normalized) > len(prefix)):
                        success = False
                        continue
                    validated_path = normalized

                if member.isdir():
                    try:
                        os.makedirs(validated_path, exist_ok=True)
                    except (OSError, IOError):
                        success = False
                        continue

                elif member.isfile():
                    parent_dir = os.path.dirname(validated_path)
                    try:
                        os.makedirs(parent_dir, exist_ok=True)
                    except (OSError, IOError):
                        success = False
                        continue

                    try:
                        with tar.extractfile(member) as src:
                            if src is None:
                                success = False
                                continue
                            with open(validated_path, 'wb') as dst:
                                while True:
                                    chunk = src.read(65536)
                                    if not chunk:
                                        break
                                    dst.write(chunk)
                    except (OSError, IOError, AttributeError):
                        success = False
                        continue

    except (tarfile.TarError, OSError, IOError):
        return False

    return success
