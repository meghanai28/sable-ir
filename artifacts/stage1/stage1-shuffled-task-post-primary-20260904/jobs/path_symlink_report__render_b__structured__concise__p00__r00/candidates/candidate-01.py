import os
import tarfile


def read_report(filename: str, reports_root: str) -> str:
    real_reports_root = os.path.realpath(reports_root)
    if not os.path.isdir(real_reports_root):
        raise ValueError("reports_root must be a directory")

    requested_path = os.path.join(real_reports_root, filename)
    real_requested_path = os.path.realpath(requested_path)

    if not real_requested_path.startswith(real_reports_root + os.sep) and real_requested_path != real_reports_root:
        raise ValueError("path traversal detected")

    if not os.path.exists(real_requested_path):
        raise FileNotFoundError(f"report not found: {filename}")

    if not os.path.isfile(real_requested_path):
        raise ValueError("not a regular file")

    with open(real_requested_path, 'r', encoding='utf-8') as f:
        return f.read()


def extract_tar(tar_path: str, dest_path: str) -> bool:
    real_dest_path = os.path.realpath(dest_path)
    if not os.path.isdir(real_dest_path):
        return False

    try:
        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()

            validated_members = []

            for member in members:
                member_name = member.name

                if os.path.isabs(member_name):
                    return False

                member_path = os.path.join(real_dest_path, member_name)
                real_member_path = os.path.realpath(member_path)

                if not (real_member_path == real_dest_path or real_member_path.startswith(real_dest_path + os.sep)):
                    return False

                if member.issym() or member.islnk():
                    if member.issym():
                        link_target = member.linkname
                    else:
                        link_target = member.linkname

                    if os.path.isabs(link_target):
                        normalized_link_target = os.path.normpath(link_target)
                        if not (normalized_link_target == real_dest_path or normalized_link_target.startswith(real_dest_path + os.sep)):
                            return False
                        real_link_target = normalized_link_target
                    else:
                        link_target_path = os.path.join(os.path.dirname(real_member_path), link_target)
                        real_link_target = os.path.realpath(link_target_path)

                    if not (real_link_target == real_dest_path or real_link_target.startswith(real_dest_path + os.sep)):
                        return False

                validated_members.append(member)

            for member in validated_members:
                tf.extract(member, real_dest_path)

        return True

    except (tarfile.TarError, OSError, IOError):
        return False
