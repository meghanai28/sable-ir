import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        dest_path = os.path.abspath(os.path.normpath(dest_path))
    except (OSError, ValueError):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()

            validated_members = []
            for member in members:
                member_name = member.name
                if os.path.isabs(member_name):
                    return False

                member_path = os.path.join(dest_path, member_name)
                try:
                    normalized_member_path = os.path.normpath(os.path.abspath(member_path))
                except (OSError, ValueError):
                    return False

                if not normalized_member_path.startswith(dest_path + os.sep) and normalized_member_path != dest_path:
                    return False

                if member.issym() or member.islnk():
                    link_target = member.linkname
                    if os.path.isabs(link_target):
                        normalized_link_target = os.path.normpath(os.path.abspath(link_target))
                        if not normalized_link_target.startswith(dest_path + os.sep) and normalized_link_target != dest_path:
                            return False
                    else:
                        link_target_path = os.path.join(os.path.dirname(normalized_member_path), link_target)
                        try:
                            normalized_link_target = os.path.normpath(os.path.abspath(link_target_path))
                        except (OSError, ValueError):
                            return False

                        if not normalized_link_target.startswith(dest_path + os.sep) and normalized_link_target != dest_path:
                            return False

                validated_members.append((member, normalized_member_path))

            for member, normalized_member_path in validated_members:
                member_dir = os.path.dirname(normalized_member_path)
                if member_dir:
                    try:
                        os.makedirs(member_dir, exist_ok=True)
                    except OSError:
                        return False

                if member.isdir():
                    try:
                        os.makedirs(normalized_member_path, exist_ok=True)
                    except OSError:
                        return False
                elif member.isfile():
                    try:
                        source = tf.extractfile(member)
                        if source is None:
                            return False
                        with open(normalized_member_path, 'wb') as f:
                            while True:
                                chunk = source.read(65536)
                                if not chunk:
                                    break
                                f.write(chunk)
                    except (OSError, IOError):
                        return False
                elif member.issym():
                    try:
                        os.symlink(member.linkname, normalized_member_path)
                    except OSError:
                        return False
                elif member.islnk():
                    try:
                        os.link(member.linkname, normalized_member_path)
                    except OSError:
                        return False
                else:
                    return False

            return True

    except (tarfile.TarError, OSError, IOError):
        return False
