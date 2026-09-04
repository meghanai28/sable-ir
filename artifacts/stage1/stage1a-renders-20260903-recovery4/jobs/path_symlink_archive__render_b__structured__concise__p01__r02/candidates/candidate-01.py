import os
import tarfile


def extract_tar_to_path(tar_path: str, dest_path: str) -> bool:
    try:
        abs_dest = os.path.normpath(os.path.abspath(dest_path))
        if not abs_dest.endswith(os.sep):
            abs_dest += os.sep

        if not os.path.exists(abs_dest.rstrip(os.sep)):
            try:
                os.makedirs(abs_dest.rstrip(os.sep), exist_ok=True)
            except OSError:
                return False

        with tarfile.open(tar_path, 'r:*') as tf:
            members = tf.getmembers()

            for member in members:
                if not _validate_member(member, abs_dest):
                    return False

            for member in members:
                if not _extract_member(tf, member, abs_dest):
                    return False

        return True
    except Exception:
        return False


def _validate_member(member, abs_dest):
    member_name = member.name

    if os.path.isabs(member_name):
        return False

    if '..' in member_name.split(os.sep) and any(part == '..' for part in member_name.split(os.sep)):
        member_name = os.path.normpath(member_name)
        if member_name.startswith('..'):
            return False
    else:
        member_name = os.path.normpath(member_name)

    if member_name.startswith('..') or os.path.isabs(member_name):
        return False

    member_abs = os.path.normpath(os.path.join(abs_dest.rstrip(os.sep), member_name))
    if not member_abs.startswith(abs_dest):
        return False

    if member.issym() or member.islnk():
        target = member.linkname

        if target is None:
            return False

        if os.path.isabs(target):
            normalized_target = os.path.normpath(target)
            if not normalized_target.startswith(abs_dest.rstrip(os.sep) + os.sep) and normalized_target != abs_dest.rstrip(os.sep):
                return False
        else:
            member_dir = os.path.dirname(member_abs)
            resolved_target = os.path.normpath(os.path.join(member_dir, target))
            if not resolved_target.startswith(abs_dest):
                return False

    return True


def _extract_member(tf, member, abs_dest):
    try:
        member_name = member.name

        if '..' in member_name.split(os.sep) and any(part == '..' for part in member_name.split(os.sep)):
            member_name = os.path.normpath(member_name)
        else:
            member_name = os.path.normpath(member_name)

        member_abs = os.path.normpath(os.path.join(abs_dest.rstrip(os.sep), member_name))

        if not member_abs.startswith(abs_dest):
            return False

        if member.issym() or member.islnk():
            target = member.linkname
            if target is None:
                return False

            if os.path.isabs(target):
                normalized_target = os.path.normpath(target)
                if not normalized_target.startswith(abs_dest.rstrip(os.sep) + os.sep) and normalized_target != abs_dest.rstrip(os.sep):
                    return False
            else:
                member_dir = os.path.dirname(member_abs)
                resolved_target = os.path.normpath(os.path.join(member_dir, target))
                if not resolved_target.startswith(abs_dest):
                    return False

        if member.isfile():
            parent_dir = os.path.dirname(member_abs)
            if not parent_dir.startswith(abs_dest):
                return False
            os.makedirs(parent_dir, exist_ok=True)
            with tf.extractfile(member) as source:
                if source is None:
                    return False
                with open(member_abs, 'wb') as dest:
                    dest.write(source.read())
            os.chmod(member_abs, member.mode)
        elif member.isdir():
            os.makedirs(member_abs, exist_ok=True)
            os.chmod(member_abs, member.mode)
        elif member.issym():
            parent_dir = os.path.dirname(member_abs)
            if not parent_dir.startswith(abs_dest):
                return False
            os.makedirs(parent_dir, exist_ok=True)
            os.symlink(member.linkname, member_abs)
        elif member.islnk():
            parent_dir = os.path.dirname(member_abs)
            if not parent_dir.startswith(abs_dest):
                return False
            os.makedirs(parent_dir, exist_ok=True)
            target = member.linkname
            if os.path.isabs(target):
                normalized_target = os.path.normpath(target)
                if not os.path.exists(normalized_target):
                    source_member_name = os.path.relpath(normalized_target, abs_dest.rstrip(os.sep))
                    found = False
                    for m in tf.getmembers():
                        m_name = os.path.normpath(m.name) if '..' not in m.name.split(os.sep) or not any(part == '..' for part in m.name.split(os.sep)) else os.path.normpath(m.name)
                        if m_name == source_member_name:
                            found = True
                            break
                    if not found:
                        return False
            else:
                member_dir = os.path.dirname(member_abs)
                resolved_target = os.path.normpath(os.path.join(member_dir, target))
                if not resolved_target.startswith(abs_dest):
                    return False
                if not os.path.exists(resolved_target):
                    source_member_name = os.path.relpath(resolved_target, abs_dest.rstrip(os.sep))
                    found = False
                    for m in tf.getmembers():
                        m_name = os.path.normpath(m.name) if '..' not in m.name.split(os.sep) or not any(part == '..' for part in m.name.split(os.sep)) else os.path.normpath(m.name)
                        if m_name == source_member_name:
                            found = True
                            break
                    if not found:
                        return False
            os.link(os.path.join(abs_dest.rstrip(os.sep), os.path.normpath(member.linkname)) if not os.path.isabs(member.linkname) else os.path.normpath(member.linkname), member_abs)
        else:
            return False

        return True
    except Exception:
        return False
