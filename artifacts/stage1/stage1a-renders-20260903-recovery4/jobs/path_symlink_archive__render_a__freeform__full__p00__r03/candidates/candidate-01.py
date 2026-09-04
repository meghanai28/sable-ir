import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(dest_path)
        dest_path = os.path.normpath(dest_path)
        os.makedirs(dest_path, exist_ok=True)
    except (OSError, ValueError):
        return False

    try:
        tar = tarfile.open(tar_path, 'r')
    except (tarfile.TarError, OSError, IOError):
        return False

    try:
        members = tar.getmembers()
    except (tarfile.TarError, OSError, IOError):
        tar.close()
        return False

    validated_members = []

    for member in members:
        if member.issym() or member.islnk():
            tar.close()
            return False

        if not (member.isfile() or member.isdir()):
            tar.close()
            return False

        name = member.name
        while name.startswith('/') or name.startswith('\\'):
            name = name[1:]
        if len(name) >= 2 and name[1] == ':':
            name = name[2:]
            while name.startswith('/') or name.startswith('\\'):
                name = name[1:]

        member_path = os.path.join(dest_path, name)
        member_path = os.path.normpath(member_path)

        try:
            common = os.path.commonpath([dest_path, member_path])
        except ValueError:
            tar.close()
            return False

        if common != dest_path:
            tar.close()
            return False

        if member_path == dest_path and member.isfile():
            tar.close()
            return False

        validated_members.append((member, member_path))

    for member, member_path in validated_members:
        try:
            if member.isdir():
                os.makedirs(member_path, exist_ok=True)
            elif member.isfile():
                parent_dir = os.path.dirname(member_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                with tar.extractfile(member) as source:
                    if source is None:
                        tar.close()
                        return False
                    with open(member_path, 'wb') as target:
                        while True:
                            chunk = source.read(65536)
                            if not chunk:
                                break
                            target.write(chunk)
                os.utime(member_path, (member.mtime, member.mtime))
        except (OSError, IOError, AttributeError):
            tar.close()
            return False

    tar.close()
    return True
