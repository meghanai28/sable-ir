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
    except (OSError, tarfile.TarError):
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
            normalized = os.path.realpath(os.path.normpath(candidate))

            if normalized == canonical_dest:
                if member.isdir():
                    pass
                else:
                    success = False
                    continue
            else:
                if not (normalized.startswith(canonical_dest + os.sep) or
                        normalized.startswith(canonical_dest + '/')):
                    success = False
                    continue

            if member.isdir():
                try:
                    os.makedirs(normalized, exist_ok=True)
                except OSError:
                    success = False
                    continue

            elif member.isfile():
                try:
                    parent_dir = os.path.dirname(normalized)
                    if parent_dir:
                        os.makedirs(parent_dir, exist_ok=True)
                except OSError:
                    success = False
                    continue

                try:
                    with open(normalized, 'wb') as out_f:
                        with tar.extractfile(member) as in_f:
                            if in_f is None:
                                success = False
                                continue
                            while True:
                                chunk = in_f.read(65536)
                                if not chunk:
                                    break
                                out_f.write(chunk)
                except (OSError, IOError):
                    success = False
                    try:
                        os.unlink(normalized)
                    except OSError:
                        pass
                    continue

    except (OSError, tarfile.TarError):
        success = False
    finally:
        tar.close()

    return success
