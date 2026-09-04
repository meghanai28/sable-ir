import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
        if not dest_path.endswith(os.sep):
            dest_path += os.sep

        with tarfile.open(tar_path, 'r:*') as tar:
            members = tar.getmembers()

            for member in members:
                member_path = member.name

                if os.path.isabs(member_path):
                    member_path = member_path.lstrip('/')

                extracted_path = os.path.abspath(os.path.normpath(os.path.join(dest_path, member_path)))

                if not extracted_path.startswith(dest_path):
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname

                    if os.path.isabs(link_target):
                        resolved_target = os.path.abspath(os.path.normpath(link_target))
                        if not resolved_target.startswith(dest_path.rstrip(os.sep) + os.sep) and resolved_target != dest_path.rstrip(os.sep):
                            return False
                    else:
                        resolved_target = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(extracted_path), link_target)))
                        if not resolved_target.startswith(dest_path):
                            return False

            def is_within_dest(member, path):
                if os.path.isabs(member.name):
                    member_path = member.name.lstrip('/')
                else:
                    member_path = member.name

                extracted_path = os.path.abspath(os.path.normpath(os.path.join(dest_path, member_path)))

                if not extracted_path.startswith(dest_path):
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname

                    if os.path.isabs(link_target):
                        resolved_target = os.path.abspath(os.path.normpath(link_target))
                        if not resolved_target.startswith(dest_path.rstrip(os.sep) + os.sep) and resolved_target != dest_path.rstrip(os.sep):
                            return False
                    else:
                        resolved_target = os.path.abspath(os.path.normpath(os.path.join(os.path.dirname(extracted_path), link_target)))
                        if not resolved_target.startswith(dest_path):
                            return False

                return True

            for member in members:
                if not is_within_dest(member, dest_path):
                    return False

            tar.extractall(path=dest_path)

            return True

    except (tarfile.TarError, OSError, IOError, ValueError):
        return False
