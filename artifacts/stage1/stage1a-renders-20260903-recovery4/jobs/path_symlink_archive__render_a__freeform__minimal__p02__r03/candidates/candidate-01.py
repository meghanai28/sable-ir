import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            for member in tar.getmembers():
                if member.issym() or member.islnk():
                    return False

                member_name = member.name.lstrip('/')
                output_path = os.path.normpath(os.path.join(dest_path, member_name))

                if not output_path.startswith(os.path.normpath(dest_path) + os.sep) and output_path != os.path.normpath(dest_path):
                    return False

                if member.isdir():
                    os.makedirs(output_path, exist_ok=True)
                elif member.isfile():
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with tar.extractfile(member) as source:
                        if source is None:
                            return False
                        with open(output_path, 'wb') as target:
                            target.write(source.read())
                else:
                    return False

        return True
    except (tarfile.TarError, OSError, IOError):
        return False
