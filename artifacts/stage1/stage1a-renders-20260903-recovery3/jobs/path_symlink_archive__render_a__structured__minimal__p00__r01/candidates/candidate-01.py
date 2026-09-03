import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    dest_path = os.path.abspath(dest_path)

    try:
        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()

            for member in members:
                if member.issym() or member.islnk():
                    return False

                member_path = os.path.join(dest_path, member.name)
                abs_member_path = os.path.abspath(member_path)

                if not abs_member_path.startswith(dest_path + os.sep) and abs_member_path != dest_path:
                    return False

            for member in members:
                if member.issym() or member.islnk():
                    return False

                member_path = os.path.join(dest_path, member.name)
                abs_member_path = os.path.abspath(member_path)

                if not abs_member_path.startswith(dest_path + os.sep) and abs_member_path != dest_path:
                    return False

                if member.isfile() or member.isdir():
                    try:
                        tar.extract(member, dest_path)
                    except (tarfile.TarError, OSError, IOError):
                        return False

            return True

    except (tarfile.TarError, OSError, IOError):
        return False
