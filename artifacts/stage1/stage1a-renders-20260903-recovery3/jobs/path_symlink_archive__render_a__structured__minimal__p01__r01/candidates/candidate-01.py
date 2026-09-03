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

                parts = member_name.split('/')
                for part in parts:
                    if part == '..' or part == '':
                        if part == '' and member_name.startswith('/'):
                            return False
                        if part == '..':
                            return False

                extracted_path = os.path.join(dest_path, member_name)
                try:
                    real_extracted_path = os.path.realpath(extracted_path)
                except (OSError, ValueError):
                    return False

                if not real_extracted_path.startswith(dest_path + os.sep) and real_extracted_path != dest_path:
                    return False

                validated_paths.append((member, real_extracted_path))

            for member, real_extracted_path in validated_paths:
                try:
                    if member.isdir():
                        os.makedirs(real_extracted_path, exist_ok=True)
                    elif member.isfile():
                        parent_dir = os.path.dirname(real_extracted_path)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)

                        with tar.extractfile(member) as fsrc:
                            if fsrc is None:
                                return False
                            with open(real_extracted_path, 'wb') as fdst:
                                while True:
                                    chunk = fsrc.read(65536)
                                    if not chunk:
                                        break
                                    fdst.write(chunk)

                        if member.mode is not None:
                            try:
                                os.chmod(real_extracted_path, member.mode)
                            except (OSError, ValueError):
                                pass
                except (OSError, IOError, tarfile.TarError, AttributeError):
                    return False

            return True

    except (OSError, IOError, tarfile.TarError):
        return False
