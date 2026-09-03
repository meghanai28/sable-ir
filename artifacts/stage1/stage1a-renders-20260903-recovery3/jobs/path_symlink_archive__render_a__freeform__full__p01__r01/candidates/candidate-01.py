import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        canonical_dest = os.path.realpath(os.path.abspath(dest_path))
    except (OSError, ValueError):
        return False

    success = True

    try:
        tar = tarfile.open(tar_path, 'r:*')
    except (tarfile.TarError, OSError, IOError):
        return False

    try:
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

            if os.path.splitdrive(member_name)[0]:
                member_name = os.path.splitdrive(member_name)[1]

            while member_name.startswith('/') or member_name.startswith('\\'):
                member_name = member_name[1:]

            candidate = os.path.join(canonical_dest, member_name)
            normalized = os.path.normpath(candidate)

            if normalized == canonical_dest:
                if member.isdir():
                    try:
                        os.makedirs(normalized, exist_ok=True)
                    except (OSError, IOError):
                        success = False
                elif member.isfile():
                    try:
                        os.makedirs(normalized, exist_ok=True)
                    except (OSError, IOError):
                        success = False
                        continue
                    try:
                        with tar.extractfile(member) as src, open(normalized, 'wb') as dst:
                            while True:
                                chunk = src.read(65536)
                                if not chunk:
                                    break
                                dst.write(chunk)
                    except (OSError, IOError, TypeError):
                        success = False
                continue

            if not normalized.startswith(canonical_dest + os.sep):
                success = False
                continue

            if member.isdir():
                try:
                    os.makedirs(normalized, exist_ok=True)
                except (OSError, IOError):
                    success = False
            elif member.isfile():
                parent_dir = os.path.dirname(normalized)
                try:
                    os.makedirs(parent_dir, exist_ok=True)
                except (OSError, IOError):
                    success = False
                    continue
                try:
                    with tar.extractfile(member) as src, open(normalized, 'wb') as dst:
                        while True:
                            chunk = src.read(65536)
                            if not chunk:
                                break
                            dst.write(chunk)
                except (OSError, IOError, TypeError):
                    success = False

    except (tarfile.TarError, OSError, IOError):
        success = False
    finally:
        tar.close()

    return success
