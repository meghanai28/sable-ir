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

            if os.path.sep == '\\':
                if len(member_name) >= 2 and member_name[1] == ':':
                    member_name = member_name[2:]
                    while member_name.startswith('/') or member_name.startswith('\\'):
                        member_name = member_name[1:]
            else:
                if member_name.startswith('/'):
                    member_name = member_name[1:]

            candidate = os.path.join(canonical_dest, member_name)
            normalized = os.path.normpath(candidate)

            if normalized == canonical_dest:
                if member.isdir():
                    try:
                        os.makedirs(normalized, exist_ok=True)
                    except OSError:
                        success = False
                    continue
                else:
                    success = False
                    continue

            prefix = canonical_dest + os.sep
            if not (normalized + os.sep).startswith(prefix):
                success = False
                continue

            if member.isdir():
                try:
                    os.makedirs(normalized, exist_ok=True)
                except OSError:
                    success = False
                continue

            if member.isfile():
                try:
                    os.makedirs(os.path.dirname(normalized), exist_ok=True)
                except OSError:
                    success = False
                    continue

                try:
                    source = tar.extractfile(member)
                    if source is None:
                        success = False
                        continue

                    try:
                        with open(normalized, 'wb') as dest_file:
                            while True:
                                chunk = source.read(65536)
                                if not chunk:
                                    break
                                dest_file.write(chunk)
                    finally:
                        source.close()
                except (OSError, IOError):
                    success = False
                    continue

    except (OSError, tarfile.TarError):
        success = False
    finally:
        try:
            tar.close()
        except (OSError, tarfile.TarError):
            success = False

    return success
