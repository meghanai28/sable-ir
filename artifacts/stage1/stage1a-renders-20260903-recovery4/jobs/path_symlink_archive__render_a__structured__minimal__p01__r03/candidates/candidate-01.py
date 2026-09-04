import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.realpath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()
            validated_paths = []

            for member in members:
                if member.issym() or member.islnk():
                    return False

                if not (member.isfile() or member.isdir()):
                    return False

                member_name = member.name

                if os.path.isabs(member_name):
                    return False

                if '..' in member_name.split(os.sep):
                    return False

                resolved_path = os.path.abspath(os.path.join(dest_path, member_name))
                resolved_path = os.path.realpath(resolved_path)

                if not resolved_path.startswith(dest_path + os.sep) and resolved_path != dest_path:
                    return False

                validated_paths.append((member, resolved_path))

            for member, resolved_path in validated_paths:
                try:
                    if member.isfile():
                        os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
                        with tar.extractfile(member) as f:
                            if f is None:
                                return False
                            with open(resolved_path, 'wb') as out_f:
                                while True:
                                    chunk = f.read(65536)
                                    if not chunk:
                                        break
                                    out_f.write(chunk)
                        os.chmod(resolved_path, member.mode)
                    elif member.isdir():
                        os.makedirs(resolved_path, exist_ok=True)
                        os.chmod(resolved_path, member.mode)
                except (OSError, IOError, tarfile.TarError):
                    return False

            return True

    except (OSError, IOError, tarfile.TarError):
        return False
