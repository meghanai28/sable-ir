import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        base_dir = os.path.abspath(os.path.normpath(dest_path))
        os.makedirs(base_dir, exist_ok=True)
    except (OSError, ValueError):
        return False

    try:
        tf = tarfile.open(tar_path, mode='r:*')
    except (tarfile.TarError, OSError, IOError):
        return False

    try:
        members = tf.getmembers()
    except (tarfile.TarError, OSError, IOError):
        tf.close()
        return False

    validated_members = []

    for member in members:
        member_name = member.name
        if os.path.isabs(member_name):
            member_name = member_name.lstrip('/')
            if not member_name:
                continue

        if member.issym() or member.islnk():
            if member.issym():
                link_target = member.linkname
            else:
                link_target = member.linkname

            if os.path.isabs(link_target):
                normalized_target = os.path.normpath(link_target)
            else:
                member_dir = os.path.dirname(member_name)
                if member_dir:
                    combined = os.path.join(member_dir, link_target)
                else:
                    combined = link_target
                normalized_target = os.path.normpath(combined)

            resolved_target = os.path.join(base_dir, normalized_target)
            resolved_target = os.path.normpath(resolved_target)

            real_base = os.path.realpath(base_dir)
            try:
                real_target = os.path.realpath(resolved_target)
            except (OSError, ValueError):
                tf.close()
                return False

            if not real_target.startswith(real_base + os.sep) and real_target != real_base:
                tf.close()
                return False

            member_path = os.path.join(base_dir, member_name)
            member_path = os.path.normpath(member_path)

            try:
                real_member_path = os.path.realpath(member_path)
            except (OSError, ValueError):
                tf.close()
                return False

            if not real_member_path.startswith(real_base + os.sep) and real_member_path != real_base:
                tf.close()
                return False

            validated_members.append((member, member_path, resolved_target))

        elif member.isdir() or member.isfile():
            member_path = os.path.join(base_dir, member_name)
            member_path = os.path.normpath(member_path)

            try:
                real_member_path = os.path.realpath(member_path)
            except (OSError, ValueError):
                tf.close()
                return False

            if not real_member_path.startswith(real_base + os.sep) and real_member_path != real_base:
                tf.close()
                return False

            validated_members.append((member, member_path, None))

        else:
            continue

    for member, member_path, link_target in validated_members:
        try:
            if member.isdir():
                os.makedirs(member_path, exist_ok=True)
            elif member.isfile():
                parent_dir = os.path.dirname(member_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                with tf.extractfile(member) as fobj:
                    if fobj is None:
                        tf.close()
                        return False
                    with open(member_path, 'wb') as outfile:
                        while True:
                            chunk = fobj.read(65536)
                            if not chunk:
                                break
                            outfile.write(chunk)
                if hasattr(member, 'mode'):
                    try:
                        os.chmod(member_path, member.mode)
                    except (OSError, IOError):
                        pass
            elif member.issym():
                parent_dir = os.path.dirname(member_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                os.symlink(member.linkname, member_path)
            elif member.islnk():
                parent_dir = os.path.dirname(member_path)
                if parent_dir:
                    os.makedirs(parent_dir, exist_ok=True)
                os.link(link_target, member_path)
        except (OSError, IOError, ValueError, AttributeError, tarfile.TarError):
            tf.close()
            return False

    tf.close()
    return True
