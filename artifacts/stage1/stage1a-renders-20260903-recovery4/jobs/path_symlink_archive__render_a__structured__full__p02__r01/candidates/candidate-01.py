import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_abs = os.path.normpath(os.path.abspath(dest_path))
    dest_prefix = dest_abs + os.sep

    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False

                if not member.isfile() and not member.isdir():
                    return False

                member_name = member.name
                candidate_path = os.path.normpath(os.path.join(dest_abs, member_name))

                if not (candidate_path == dest_abs or candidate_path.startswith(dest_prefix)):
                    return False

                if member.isdir():
                    try:
                        os.makedirs(candidate_path, exist_ok=True)
                    except OSError:
                        return False
                elif member.isfile():
                    try:
                        parent_dir = os.path.dirname(candidate_path)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)
                        with tar.extractfile(member) as fsrc:
                            if fsrc is None:
                                return False
                            with open(candidate_path, 'wb') as fdst:
                                while True:
                                    chunk = fsrc.read(65536)
                                    if not chunk:
                                        break
                                    fdst.write(chunk)
                    except (OSError, tarfile.ExtractError, TypeError):
                        return False
    except (OSError, tarfile.TarError):
        return False

    return True
